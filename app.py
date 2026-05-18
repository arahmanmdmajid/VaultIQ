"""
VaultIQ — Governed Document Intelligence
Streamlit chat interface for the Vision RAG pipeline.

Flow:
  1. User uploads a PDF → rendered on-demand with PyMuPDF
  2. PDF is indexed by PageIndex (visual reasoning graph, ~30s)
  3. User asks a question → PageIndex returns relevant page numbers
  4. Those pages are compressed to JPEG and sent to Llama 4 Scout (Groq)
  5. Answer + source page images are displayed inline
"""

import base64
import io
import os
import re
import tempfile
import time

import fitz  # PyMuPDF
import requests
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from pageindex import PageIndexClient
from PIL import Image

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()

VISION_MODEL       = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_IMAGES_PER_REQ = 5    # Groq hard limit
RENDER_DPI         = 150  # page render resolution


# ─── Clients (cached so they are not re-created on every rerun) ───────────────

@st.cache_resource
def get_clients():
    pi  = PageIndexClient(api_key=os.getenv("PAGEINDEX_API_KEY"))
    grq = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return pi, grq

pi_client, groq_client = get_clients()


# ─── Pipeline helpers ─────────────────────────────────────────────────────────

def compress_image(img_bytes: bytes, max_width: int = 1024, quality: int = 82) -> bytes:
    """Resize and re-encode as JPEG to reduce token usage."""
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def render_page(pdf_bytes: bytes, page_num: int) -> bytes:
    """Render a single 1-based page from PDF bytes → compressed JPEG bytes."""
    doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num - 1]
    mat  = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()
    return compress_image(pix.tobytes("png"))


def upload_pdf_to_pageindex(pdf_bytes: bytes) -> str:
    """Write PDF bytes to a temp file, upload to PageIndex, return doc_id."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = pi_client.submit_document(file_path=tmp_path)
        return (
            result.get("doc_id")
            or result.get("id")
            or result.get("document_id")
        )
    finally:
        os.unlink(tmp_path)


def wait_for_indexing(doc_id: str, timeout: int = 180) -> bool:
    """Poll until PageIndex finishes building the reasoning graph."""
    for _ in range(timeout):
        if pi_client.is_retrieval_ready(doc_id):
            return True
        time.sleep(1)
    return False


PAGEINDEX_CHAT_URL = "https://api.pageindex.ai/chat/completions"


def retrieve_pages(doc_id: str, question: str) -> tuple[list[int], dict]:
    """
    Use the PageIndex Chat API (the non-deprecated successor to submit_query/get_retrieval)
    to find which pages are relevant to the question.

    With enable_citations=True, PageIndex embeds page references in its answer as
    citation tags: <doc=filename.pdf;page=N>
    We parse those tags to get the page numbers, then feed those pages to Groq Vision.

    Returns (sorted list of 1-based page numbers, raw API response for debugging).
    """
    payload = {
        "doc_id"          : doc_id,
        "messages"        : [{"role": "user", "content": question}],
        "stream"          : False,
        "enable_citations": True,
    }
    headers = {
        "api_key"     : os.getenv("PAGEINDEX_API_KEY"),
        "Content-Type": "application/json",
    }
    response = requests.post(PAGEINDEX_CHAT_URL, json=payload, headers=headers, timeout=60)
    result   = response.json()

    content  = (
        result.get("choices", [{}])[0]
              .get("message", {})
              .get("content", "")
    )
    page_nums = _parse_citation_pages(content)
    return page_nums, result


def _parse_citation_pages(text: str) -> list[int]:
    """
    Extract page numbers from PageIndex citation tags.
    Handles formats:
      <doc=filename.pdf;page=3>
      [page=3]
      page 3  (plain fallback)
    """
    pages = set()

    # Primary: <doc=...;page=N>
    for m in re.finditer(r"<doc=[^>]*?;page=(\d+)>", text):
        pages.add(int(m.group(1)))

    # Fallback: [page=N] or [p=N]
    if not pages:
        for m in re.finditer(r"\[(?:page|p)=(\d+)\]", text):
            pages.add(int(m.group(1)))

    return sorted(pages)


def answer_from_images(question: str, page_images: list, language: str) -> str:
    """Send question + JPEG pages to Llama 4 Scout via Groq."""
    if not page_images:
        return "No relevant pages were found for this question."

    batch       = page_images[:MAX_IMAGES_PER_REQ]
    page_labels = [label for label, _ in batch]

    if language == "ar":
        prompt = (
            "أنت محلل خبير في الوثيقة المرفوعة. "
            f"الصفحات المرفقة {page_labels} اختارها PageIndex كأكثر الصفحات صلة. "
            "أجب بالعربية فقط. اذكر رقم الصفحة لكل معلومة. "
            "إذا لم تجد الإجابة، قل ذلك صراحة.\n\n"
            f"السؤال: {question}"
        )
    else:
        prompt = (
            f"Pages {page_labels} were selected by PageIndex as most relevant. "
            "Answer using ONLY what is visible in these page images. "
            "Cite the page label for every fact (e.g. [p.10]). "
            "If the answer is not visible in the provided pages, say so explicitly.\n\n"
            f"Question: {question}"
        )

    content = [{"type": "text", "text": prompt}]
    for _, img_bytes in batch:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "type"      : "image_url",
            "image_url" : {"url": f"data:image/jpeg;base64,{b64}"},
        })

    response = groq_client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def detect_language(text: str) -> str:
    """Return 'ar' if the text contains Arabic characters, else 'en'."""
    return "ar" if re.search(r"[؀-ۿ]", text) else "en"


# ─── Session state init ───────────────────────────────────────────────────────

defaults = {
    "messages"   : [],
    "doc_id"     : None,
    "pdf_name"   : None,
    "pdf_bytes"  : None,
    "page_cache" : {},   # {page_num: jpeg_bytes}
    "total_pages": 0,
    "indexed"    : False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="VaultIQ",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Tighten up source image captions */
    .element-container figcaption { font-size: 0.72rem; color: #888; text-align: center; }
    /* Slightly larger chat text */
    .stChatMessage p { font-size: 0.95rem; line-height: 1.55; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏛️ VaultIQ")
    st.caption("Governed Document Intelligence")
    st.divider()

    st.markdown("**Upload a PDF**")
    uploaded = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded:
        # Detect new file
        if uploaded.name != st.session_state.pdf_name:
            pdf_bytes = uploaded.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            total = len(doc)
            doc.close()

            st.session_state.pdf_name    = uploaded.name
            st.session_state.pdf_bytes   = pdf_bytes
            st.session_state.total_pages = total
            st.session_state.doc_id      = None
            st.session_state.page_cache  = {}
            st.session_state.messages    = []
            st.session_state.indexed     = False

        st.success(f"📄 {st.session_state.pdf_name}")
        st.caption(f"{st.session_state.total_pages} pages")

        if not st.session_state.indexed:
            if st.button("Index with PageIndex ⚡", type="primary", use_container_width=True):
                with st.spinner("Uploading to PageIndex..."):
                    doc_id = upload_pdf_to_pageindex(st.session_state.pdf_bytes)
                    st.session_state.doc_id = doc_id

                with st.spinner("Building visual reasoning graph… (~30s)"):
                    ready = wait_for_indexing(doc_id)

                if ready:
                    st.session_state.indexed = True
                    st.rerun()
                else:
                    st.error("Indexing timed out — try again.")
        else:
            st.success("✅ Indexed and ready")
            if st.button("Clear chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

    st.divider()
    debug_mode = st.toggle("🔍 Debug mode", value=False)
    st.divider()
    st.caption("**Stack**")
    st.caption("PageIndex · Groq · Llama 4 Scout · Streamlit")
    st.caption("TechEx Intelligent Enterprise Solutions Hackathon")


# ─── Main area ────────────────────────────────────────────────────────────────

st.header("VaultIQ — Governed Document Intelligence")
st.caption(
    "Upload any PDF, ask questions in **Arabic or English**. "
    "Every answer is grounded in the source pages shown below it."
)

# Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("page_images"):
            n = len(msg["page_images"])
            cols = st.columns(min(n, MAX_IMAGES_PER_REQ))
            for col, (label, img_bytes) in zip(cols, msg["page_images"]):
                col.image(img_bytes, caption=f"Source · {label}", use_container_width=True)

# Guard: must index before chatting
if not st.session_state.indexed:
    st.info("⬅️  Upload a PDF and click **Index with PageIndex** to start.")
    st.stop()

# Chat input
question = st.chat_input("Ask a question about your document…")

if question:
    # Append and render user bubble
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Assistant pipeline
    with st.chat_message("assistant"):
        with st.spinner("Finding relevant pages…"):
            page_nums, raw_retrieval = retrieve_pages(st.session_state.doc_id, question)

        if debug_mode:
            with st.expander("🔍 Raw PageIndex response", expanded=True):
                st.json(raw_retrieval)

        if not page_nums:
            # PageIndex answered but returned no parseable page citations.
            # Surface its text answer as a fallback so the user still gets something useful.
            pi_answer = (
                raw_retrieval.get("choices", [{}])[0]
                             .get("message", {})
                             .get("content", "")
            )
            if pi_answer:
                answer = (
                    f"{pi_answer}\n\n"
                    "_⚠️ No specific page citations were returned — "
                    "answer is from PageIndex text reasoning, not visual page reading._"
                )
            else:
                answer = (
                    "PageIndex did not return relevant content for this question. "
                    "Try rephrasing or check that the document covers this topic."
                )
            st.markdown(answer)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "page_images": []}
            )
        else:
            # Render pages on-demand, cache for future turns
            page_images = []
            for p in page_nums[:MAX_IMAGES_PER_REQ]:
                if p not in st.session_state.page_cache:
                    st.session_state.page_cache[p] = render_page(
                        st.session_state.pdf_bytes, p
                    )
                page_images.append((f"p{p}", st.session_state.page_cache[p]))

            lang = detect_language(question)

            with st.spinner("Reading pages…"):
                answer = answer_from_images(question, page_images, lang)

            st.markdown(answer)

            # Inline source images
            cols = st.columns(len(page_images))
            for col, (label, img_bytes) in zip(cols, page_images):
                col.image(img_bytes, caption=f"Source · {label}", use_container_width=True)

            st.session_state.messages.append({
                "role"       : "assistant",
                "content"    : answer,
                "page_images": page_images,
            })
