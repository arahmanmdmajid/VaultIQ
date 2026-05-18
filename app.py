"""
VaultIQ — Governed Document Intelligence
Streamlit chat interface for the Vision RAG pipeline.

Tabs:
  💬 Chat            — main user-facing interface
  🛠️ Developer       — pipeline timings, raw JSON, model info, query log
"""

import base64
import io
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from groq import Groq
from pageindex import PageIndexClient
from PIL import Image

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv()

VISION_MODEL        = "meta-llama/llama-4-scout-17b-16e-instruct"
PAGEINDEX_MODEL     = "PageIndex Visual Reasoning (chat/completions)"
MAX_IMAGES_PER_REQ  = 5
RENDER_DPI          = 150
PAGEINDEX_CHAT_URL  = "https://api.pageindex.ai/chat/completions"

ROOT = Path(__file__).parent

DEMO_DOCS = {
    "en": {
        "label"   : "Madinah Tranquil Livable City Report 2024",
        "pdf_path": ROOT / "data" / "tranquil_en_subset.pdf",
        "doc_id"  : "pi-cmp57ce4000u001qw6ueq8vz3",
        "pages"   : 14,
        "flag"    : "🇬🇧",
    },
    "ar": {
        "label"   : "تقرير مدينة المدينة المنورة الهادئة للعيش 2024",
        "pdf_path": ROOT / "data" / "tranquil_ar_subset.pdf",
        "doc_id"  : "pi-cmp57cg9n00u201qw4bkt2o1i",
        "pages"   : 14,
        "flag"    : "🇸🇦",
    },
}

SAMPLE_QUESTIONS = [
    "What are the livability indicators used in this report?",
    "What is the population of Madinah according to the report?",
    "What sustainability goals were achieved in 2024?",
    "What are the key challenges facing Madinah's urban development?",
]


# ─── Clients ──────────────────────────────────────────────────────────────────

@st.cache_resource
def get_clients():
    return (
        PageIndexClient(api_key=os.getenv("PAGEINDEX_API_KEY")),
        Groq(api_key=os.getenv("GROQ_API_KEY")),
    )

pi_client, groq_client = get_clients()


# ─── Image helpers ────────────────────────────────────────────────────────────

def compress_image(img_bytes: bytes, max_width: int = 1024, quality: int = 82) -> bytes:
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
    doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num - 1]
    mat  = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    doc.close()
    return compress_image(pix.tobytes("png"))


def render_image_gallery(page_images: list, thumb_width: int = 140):
    """
    Render page images as clickable thumbnails.
    Clicking a thumbnail opens a full-screen lightbox overlay.
    The overlay is injected into window.parent.document to escape the iframe
    and truly cover the full Streamlit page.
    """
    if not page_images:
        return

    thumbs_html = ""
    for label, img_bytes in page_images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        src = f"data:image/jpeg;base64,{b64}"
        thumbs_html += f"""
        <div style="text-align:center;">
          <img
            src="{src}"
            style="width:{thumb_width}px;height:auto;border-radius:6px;
                   cursor:zoom-in;border:1px solid #dee2e6;
                   transition:box-shadow .15s;box-shadow:0 1px 4px rgba(0,0,0,.1);"
            onmouseover="this.style.boxShadow='0 4px 14px rgba(0,0,0,.25)'"
            onmouseout="this.style.boxShadow='0 1px 4px rgba(0,0,0,.1)'"
            onclick="openLightbox('{src}')"
            title="Click to expand"
          />
          <div style="font-size:11px;color:#888;margin-top:5px;">Source · {label}</div>
        </div>"""

    html = f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;padding:6px 0 2px;">
      {thumbs_html}
    </div>

    <script>
    function openLightbox(src) {{
      // Remove any existing overlay first
      var old = window.parent.document.getElementById('vaultiq-lightbox');
      if (old) old.remove();

      // Overlay backdrop
      var overlay = window.parent.document.createElement('div');
      overlay.id = 'vaultiq-lightbox';
      overlay.style.cssText = [
        'position:fixed','top:0','left:0','width:100%','height:100%',
        'background:rgba(0,0,0,0.88)','z-index:99999',
        'display:flex','align-items:center','justify-content:center',
        'cursor:zoom-out'
      ].join(';');

      // Full-size image
      var img = window.parent.document.createElement('img');
      img.src = src;
      img.style.cssText = [
        'max-width:88vw','max-height:88vh',
        'border-radius:8px','cursor:default',
        'box-shadow:0 12px 48px rgba(0,0,0,0.6)'
      ].join(';');
      img.onclick = function(e) {{ e.stopPropagation(); }};

      // Close button
      var btn = window.parent.document.createElement('span');
      btn.innerHTML = '&#x2715;';
      btn.title = 'Close (Esc)';
      btn.style.cssText = [
        'position:fixed','top:22px','right:30px',
        'font-size:2rem','color:white','cursor:pointer',
        'font-weight:bold','line-height:1','opacity:0.8',
        'transition:opacity .15s','user-select:none'
      ].join(';');
      btn.onmouseover = function() {{ this.style.opacity='1'; }};
      btn.onmouseout  = function() {{ this.style.opacity='0.8'; }};
      btn.onclick = function(e) {{ e.stopPropagation(); overlay.remove(); }};

      overlay.onclick = function() {{ overlay.remove(); }};
      overlay.appendChild(img);
      overlay.appendChild(btn);
      window.parent.document.body.appendChild(overlay);

      // Escape key to close
      function onKey(e) {{
        if (e.key === 'Escape') {{
          overlay.remove();
          window.parent.document.removeEventListener('keydown', onKey);
        }}
      }}
      window.parent.document.addEventListener('keydown', onKey);
    }}
    </script>
    """

    row_height = thumb_width + 40   # thumb height approx + label + padding
    components.html(html, height=row_height, scrolling=False)


# ─── Pipeline helpers ─────────────────────────────────────────────────────────

def upload_pdf_to_pageindex(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        result = pi_client.submit_document(file_path=tmp_path)
        return result.get("doc_id") or result.get("id") or result.get("document_id")
    finally:
        os.unlink(tmp_path)


def wait_for_indexing(doc_id: str, timeout: int = 180) -> bool:
    for _ in range(timeout):
        if pi_client.is_retrieval_ready(doc_id):
            return True
        time.sleep(1)
    return False


def retrieve_pages(doc_id: str, question: str) -> tuple[list[int], dict, float]:
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
    t0       = time.perf_counter()
    response = requests.post(PAGEINDEX_CHAT_URL, json=payload, headers=headers, timeout=60)
    elapsed  = (time.perf_counter() - t0) * 1000
    result   = response.json()
    content  = (
        result.get("choices", [{}])[0]
              .get("message", {})
              .get("content", "")
    )
    return _parse_citation_pages(content), result, elapsed


def _parse_citation_pages(text: str) -> list[int]:
    pages = set()
    for m in re.finditer(r"<doc=[^>]*?;page=(\d+)>", text):
        pages.add(int(m.group(1)))
    if not pages:
        for m in re.finditer(r"\[(?:page|p)=(\d+)\]", text):
            pages.add(int(m.group(1)))
    return sorted(pages)


def answer_from_images(
    question: str, page_images: list, language: str
) -> tuple[str, dict, float]:
    if not page_images:
        return "No relevant pages were found for this question.", {}, 0.0

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
            "If the answer is not visible, say so explicitly.\n\n"
            f"Question: {question}"
        )

    content = [{"type": "text", "text": prompt}]
    for _, img_bytes in batch:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "type"      : "image_url",
            "image_url" : {"url": f"data:image/jpeg;base64,{b64}"},
        })

    t0       = time.perf_counter()
    response = groq_client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0,
    )
    elapsed = (time.perf_counter() - t0) * 1000

    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens"    : response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens"     : response.usage.total_tokens,
        }

    return response.choices[0].message.content.strip(), usage, elapsed


def detect_language(text: str) -> str:
    return "ar" if re.search(r"[؀-ۿ]", text) else "en"


# ─── Session state helpers ────────────────────────────────────────────────────

def _save_current_lang_state():
    lang = st.session_state.get("demo_lang", "en")
    if st.session_state.get("is_demo"):
        st.session_state[f"messages_{lang}"]   = list(st.session_state.messages)
        st.session_state[f"page_cache_{lang}"] = dict(st.session_state.page_cache)


def load_demo(lang: str):
    _save_current_lang_state()
    demo      = DEMO_DOCS[lang]
    pdf_bytes = demo["pdf_path"].read_bytes()
    st.session_state.doc_id      = demo["doc_id"]
    st.session_state.pdf_name    = demo["pdf_path"].name
    st.session_state.pdf_bytes   = pdf_bytes
    st.session_state.total_pages = demo["pages"]
    st.session_state.indexed     = True
    st.session_state.is_demo     = True
    st.session_state.demo_lang   = lang
    st.session_state.messages    = list(st.session_state.get(f"messages_{lang}", []))
    st.session_state.page_cache  = dict(st.session_state.get(f"page_cache_{lang}", {}))


# ─── Session state init ───────────────────────────────────────────────────────

if "initialized" not in st.session_state:
    st.session_state.initialized   = True
    st.session_state.messages      = []
    st.session_state.messages_en   = []
    st.session_state.messages_ar   = []
    st.session_state.doc_id        = None
    st.session_state.pdf_name      = None
    st.session_state.pdf_bytes     = None
    st.session_state.total_pages   = 0
    st.session_state.indexed       = False
    st.session_state.is_demo       = False
    st.session_state.demo_lang     = "en"
    st.session_state.page_cache    = {}
    st.session_state.page_cache_en = {}
    st.session_state.page_cache_ar = {}
    st.session_state.pipeline_log  = []
    st.session_state.last_stats    = None
    st.session_state.last_raw      = None
    load_demo("en")


# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="VaultIQ",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stChatMessage p { font-size: 0.95rem; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏛️ VaultIQ")
    st.caption("Governed Document Intelligence")
    st.divider()

    st.markdown("**📋 Sample Document**")
    st.caption("Pre-indexed and ready to query")

    col_en, col_ar = st.columns(2)
    with col_en:
        btn_type = "primary" if (st.session_state.demo_lang == "en" and st.session_state.is_demo) else "secondary"
        if st.button("🇬🇧 English", use_container_width=True, type=btn_type):
            load_demo("en")
            st.rerun()
    with col_ar:
        btn_type = "primary" if (st.session_state.demo_lang == "ar" and st.session_state.is_demo) else "secondary"
        if st.button("🇸🇦 Arabic", use_container_width=True, type=btn_type):
            load_demo("ar")
            st.rerun()

    if st.session_state.is_demo:
        demo_info = DEMO_DOCS[st.session_state.demo_lang]
        st.success(f"✅ {demo_info['label']}")
        st.caption(f"{demo_info['pages']} pages · Madinah Development Authority")

    st.divider()

    with st.expander("📤 Upload your own document"):
        uploaded = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
        if uploaded:
            if uploaded.name != st.session_state.pdf_name:
                pdf_bytes = uploaded.read()
                doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
                total = len(doc)
                doc.close()
                st.session_state.pdf_name    = uploaded.name
                st.session_state.pdf_bytes   = pdf_bytes
                st.session_state.total_pages = total
                st.session_state.doc_id      = None
                st.session_state.page_cache  = {}
                st.session_state.messages    = []
                st.session_state.indexed     = False
                st.session_state.is_demo     = False

            st.info(f"📄 {st.session_state.pdf_name} · {st.session_state.total_pages} pages")

            if not st.session_state.indexed:
                if st.button("Index with PageIndex ⚡", type="primary", use_container_width=True):
                    with st.spinner("Uploading to PageIndex..."):
                        doc_id = upload_pdf_to_pageindex(st.session_state.pdf_bytes)
                        st.session_state.doc_id = doc_id
                    with st.spinner("Building reasoning graph… (~30s)"):
                        ready = wait_for_indexing(doc_id)
                    if ready:
                        st.session_state.indexed = True
                        st.rerun()
                    else:
                        st.error("Indexing timed out — try again.")
            else:
                st.success("✅ Indexed and ready")

    st.divider()

    if st.session_state.indexed:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            if st.session_state.is_demo:
                st.session_state[f"messages_{st.session_state.demo_lang}"] = []
            st.rerun()

    st.divider()
    st.caption("**Stack**")
    st.caption("PageIndex · Groq · Llama 4 Scout · Streamlit")
    st.caption("TechEx Intelligent Enterprise Solutions Hackathon")


# ─── Main tabs ────────────────────────────────────────────────────────────────

st.header("VaultIQ — Governed Document Intelligence")
st.caption(
    "Ask questions in **Arabic or English**. "
    "Every answer is grounded in the source pages — click any thumbnail to expand it."
)

tab_chat, tab_dev = st.tabs(["💬 Chat", "🛠️ Developer Dashboard"])


# ── Chat tab ──────────────────────────────────────────────────────────────────

with tab_chat:

    # Welcome card — only shown when no messages exist yet
    if not st.session_state.messages and st.session_state.is_demo:
        demo_info = DEMO_DOCS[st.session_state.demo_lang]
        st.info(
            f"**{demo_info['flag']} Sample document ready** — "
            f"_{demo_info['label']}_\n\n"
            "This report covers Madinah's urban livability metrics, population, "
            "transport, healthcare, sustainability goals, and neighbourhood scores. "
            "Ask anything below, or try one of the sample questions. "
            "You can also upload your own PDF from the sidebar."
        )
        st.markdown("**Try asking:**")
        for q in SAMPLE_QUESTIONS:
            if st.button(q, key=f"sq_{q}"):
                st.session_state["prefill_question"] = q
                st.rerun()

    # Render existing chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("page_images"):
                render_image_gallery(msg["page_images"])

    # Guard
    if not st.session_state.indexed:
        st.info("⬅️  Upload a PDF and click **Index with PageIndex** to start.")

    # ── Chat input — page level so it always appears at the very bottom ───────
    # Evaluated outside the tab block but response is rendered inside tab_chat
    # by re-entering the tab context below.

# ── Developer Dashboard tab ───────────────────────────────────────────────────

with tab_dev:
    st.subheader("Pipeline Configuration")
    c1, c2, c3 = st.columns(3)
    c1.metric("Vision Model", "Llama 4 Scout")
    c2.metric("Retrieval", "PageIndex Chat API")
    c3.metric("Max Images / Request", MAX_IMAGES_PER_REQ)

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Active Document**")
        st.code(
            f"Name    : {st.session_state.pdf_name or '—'}\n"
            f"Pages   : {st.session_state.total_pages or '—'}\n"
            f"Doc ID  : {st.session_state.doc_id or '—'}\n"
            f"Indexed : {st.session_state.indexed}",
            language="yaml",
        )
    with cc2:
        st.markdown("**Models & Endpoints**")
        st.code(
            f"Vision LLM  : {VISION_MODEL}\n"
            f"Retrieval   : {PAGEINDEX_CHAT_URL}\n"
            f"Render DPI  : {RENDER_DPI}\n"
            f"Image limit : {MAX_IMAGES_PER_REQ} per request",
            language="yaml",
        )

    st.divider()
    st.subheader("Last Query")
    if st.session_state.last_stats:
        s = st.session_state.last_stats
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("PageIndex", f"{s['pageindex_ms']:.0f} ms")
        m2.metric("Page Render", f"{s['render_ms']:.0f} ms")
        m3.metric("Groq Vision", f"{s['groq_ms']:.0f} ms")
        m4.metric("Total", f"{s['total_ms']:.0f} ms")
        st.markdown(
            f"**Question:** {s['question']}  \n"
            f"**Pages retrieved:** `{s['pages_retrieved']}`  "
            f"· **Images sent:** `{s['images_sent']}`  "
            f"· **Language:** `{s['language']}`"
        )
        if s.get("token_usage"):
            u = s["token_usage"]
            st.markdown(
                f"**Groq tokens** — Prompt: `{u.get('prompt_tokens','?')}`  "
                f"· Completion: `{u.get('completion_tokens','?')}`  "
                f"· Total: `{u.get('total_tokens','?')}`"
            )
        with st.expander("📄 Raw PageIndex response"):
            st.json(st.session_state.last_raw or {})
    else:
        st.caption("No queries yet — ask a question in the Chat tab.")

    st.divider()
    st.subheader(f"Query Log — {len(st.session_state.pipeline_log)} queries this session")
    if st.session_state.pipeline_log:
        log_rows = []
        for entry in reversed(st.session_state.pipeline_log):
            log_rows.append({
                "Time"        : entry["timestamp"],
                "Question"    : entry["question"][:60] + ("…" if len(entry["question"]) > 60 else ""),
                "Pages"       : str(entry["pages_retrieved"]),
                "Lang"        : entry["language"],
                "PI (ms)"     : f"{entry['pageindex_ms']:.0f}",
                "Render (ms)" : f"{entry['render_ms']:.0f}",
                "Groq (ms)"   : f"{entry['groq_ms']:.0f}",
                "Total (ms)"  : f"{entry['total_ms']:.0f}",
                "Tokens"      : entry.get("token_usage", {}).get("total_tokens", "—"),
            })
        st.dataframe(log_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("Query log is empty.")


# ─── Chat input (always at page bottom) ──────────────────────────────────────

if not st.session_state.indexed:
    st.stop()

prefill  = st.session_state.pop("prefill_question", None)
question = st.chat_input("Ask a question about your document…") or prefill

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    # All pipeline work and response rendering happens inside tab_chat so that
    # spinners are scoped to the tab and don't dim the full page.
    with tab_chat:
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):

            # Step 1 — PageIndex retrieval
            with st.spinner("Finding relevant pages…"):
                page_nums, raw_retrieval, pi_ms = retrieve_pages(
                    st.session_state.doc_id, question
                )
            st.session_state.last_raw = raw_retrieval

            # Step 2 — Render pages on-demand
            render_t0   = time.perf_counter()
            page_images = []
            for p in page_nums[:MAX_IMAGES_PER_REQ]:
                if p not in st.session_state.page_cache:
                    st.session_state.page_cache[p] = render_page(
                        st.session_state.pdf_bytes, p
                    )
                page_images.append((f"p{p}", st.session_state.page_cache[p]))
            render_ms = (time.perf_counter() - render_t0) * 1000

            lang = detect_language(question)

            # Step 3 — Groq Vision (or fallback)
            if not page_nums:
                pi_answer = (
                    raw_retrieval.get("choices", [{}])[0]
                                 .get("message", {})
                                 .get("content", "")
                )
                answer = (
                    f"{pi_answer}\n\n"
                    "_⚠️ No specific page citations were returned — "
                    "answer is from PageIndex text reasoning, not visual page reading._"
                    if pi_answer else
                    "PageIndex did not return relevant content for this question. "
                    "Try rephrasing or check that the document covers this topic."
                )
                token_usage, groq_ms = {}, 0.0
            else:
                with st.spinner("Reading pages…"):
                    answer, token_usage, groq_ms = answer_from_images(
                        question, page_images, lang
                    )

            # Display answer and thumbnails
            st.markdown(answer)
            if page_images:
                render_image_gallery(page_images)

    # Record stats
    total_ms = pi_ms + render_ms + groq_ms
    stats = {
        "timestamp"      : datetime.now().strftime("%H:%M:%S"),
        "question"       : question,
        "pages_retrieved": page_nums,
        "images_sent"    : len(page_images),
        "language"       : lang,
        "pageindex_ms"   : pi_ms,
        "render_ms"      : render_ms,
        "groq_ms"        : groq_ms,
        "total_ms"       : total_ms,
        "token_usage"    : token_usage,
    }
    st.session_state.last_stats = stats
    st.session_state.pipeline_log.append(stats)

    # Persist message to session (and to per-language store)
    st.session_state.messages.append({
        "role"       : "assistant",
        "content"    : answer,
        "page_images": page_images,
    })
    if st.session_state.is_demo:
        lk = st.session_state.demo_lang
        st.session_state[f"messages_{lk}"]   = list(st.session_state.messages)
        st.session_state[f"page_cache_{lk}"] = dict(st.session_state.page_cache)
