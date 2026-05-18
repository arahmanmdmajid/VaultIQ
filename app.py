"""
VaultIQ — Governed Document Intelligence
Streamlit chat interface for the Vision RAG pipeline.

Tabs:
  💬 Chat            — main user-facing interface
  🛠️ Developer       — pipeline flow, timings, raw JSON, query log
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

VISION_MODEL       = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_IMAGES_PER_REQ = 5
RENDER_DPI         = 150
PAGEINDEX_CHAT_URL = "https://api.pageindex.ai/chat/completions"
ROOT               = Path(__file__).parent

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

# All user-facing strings, keyed by language
UI = {
    "en": {
        "welcome_title" : "Sample document ready",
        "welcome_body"  : (
            "This report covers Madinah's urban livability metrics, population, "
            "transport, healthcare, sustainability goals, and neighbourhood scores."
        ),
        "quick_questions": "💡 Quick questions",
        "chat_input"    : "Ask a question about your document…",
        "no_pages"      : (
            "PageIndex did not return relevant content for this question. "
            "Try rephrasing or check that the document covers this topic."
        ),
        "no_citations"  : (
            "\n\n_⚠️ No specific page citations were returned — "
            "answer is from PageIndex text reasoning, not visual page reading._"
        ),
        "indexed_ready" : "Indexed and ready",
        "upload_prompt" : "⬅️  Upload a PDF and click **Index with PageIndex** to start.",
        "sample_doc"    : "📋 Sample Document",
        "sample_caption": "Pre-indexed and ready to query",
        "mda_caption"   : "pages · Madinah Development Authority",
    },
    "ar": {
        "welcome_title" : "الوثيقة النموذجية جاهزة",
        "welcome_body"  : (
            "يتناول هذا التقرير مؤشرات قابلية العيش في المدينة المنورة، "
            "والسكان، والنقل، والرعاية الصحية، وأهداف الاستدامة، ودرجات الأحياء."
        ),
        "quick_questions": "💡 أسئلة سريعة",
        "chat_input"    : "اطرح سؤالاً حول وثيقتك…",
        "no_pages"      : (
            "لم يُرجع PageIndex محتوى ذا صلة بهذا السؤال. "
            "حاول إعادة الصياغة أو تحقق من أن الوثيقة تغطي هذا الموضوع."
        ),
        "no_citations"  : (
            "\n\n_⚠️ لم تُرجع استشهادات صفحات محددة — "
            "الإجابة مستندة إلى استدلال PageIndex النصي، لا القراءة البصرية للصفحات._"
        ),
        "indexed_ready" : "مُفهرسة وجاهزة",
        "upload_prompt" : "⬅️  ارفع ملف PDF وانقر على **فهرسة بـ PageIndex** للبدء.",
        "sample_doc"    : "📋 الوثيقة النموذجية",
        "sample_caption": "مُفهرسة مسبقاً وجاهزة للاستعلام",
        "mda_caption"   : "صفحة · هيئة تطوير منطقة المدينة المنورة",
    },
}

SAMPLE_QUESTIONS = {
    "en": [
        "What are the livability indicators used in this report?",
        "What is the population of Madinah according to the report?",
        "What sustainability goals were achieved in 2024?",
        "What are the key challenges facing Madinah's urban development?",
    ],
    "ar": [
        "ما هي مؤشرات قابلية العيش المستخدمة في هذا التقرير؟",
        "ما هو عدد سكان المدينة المنورة وفقاً للتقرير؟",
        "ما هي أبرز إنجازات التنمية المستدامة في عام 2024؟",
        "ما هي أبرز التحديات التي تواجه التطوير العمراني في المدينة المنورة؟",
    ],
}


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
    """Thumbnails with a full-screen lightbox via window.parent injection."""
    if not page_images:
        return

    thumbs_html = ""
    for label, img_bytes in page_images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        src = f"data:image/jpeg;base64,{b64}"
        thumbs_html += f"""
        <div style="text-align:center;">
          <img src="{src}"
            style="width:{thumb_width}px;height:auto;border-radius:6px;
                   cursor:zoom-in;border:1px solid #dee2e6;
                   transition:box-shadow .15s;box-shadow:0 1px 4px rgba(0,0,0,.1);"
            onmouseover="this.style.boxShadow='0 4px 14px rgba(0,0,0,.25)'"
            onmouseout="this.style.boxShadow='0 1px 4px rgba(0,0,0,.1)'"
            onclick="openLightbox('{src}')"
            title="Click to expand" />
          <div style="font-size:11px;color:#888;margin-top:5px;">Source · {label}</div>
        </div>"""

    html = f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;padding:6px 0 2px;">
      {thumbs_html}
    </div>
    <script>
    function openLightbox(src) {{
      var old = window.parent.document.getElementById('vaultiq-lightbox');
      if (old) old.remove();
      var overlay = window.parent.document.createElement('div');
      overlay.id = 'vaultiq-lightbox';
      overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.88);z-index:99999;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
      var img = window.parent.document.createElement('img');
      img.src = src;
      img.style.cssText = 'max-width:88vw;max-height:88vh;border-radius:8px;cursor:default;box-shadow:0 12px 48px rgba(0,0,0,0.6);';
      img.onclick = function(e) {{ e.stopPropagation(); }};
      var btn = window.parent.document.createElement('span');
      btn.innerHTML = '&#x2715;';
      btn.title = 'Close (Esc)';
      btn.style.cssText = 'position:fixed;top:22px;right:30px;font-size:2rem;color:white;cursor:pointer;font-weight:bold;opacity:0.8;transition:opacity .15s;user-select:none;';
      btn.onmouseover = function() {{ this.style.opacity='1'; }};
      btn.onmouseout  = function() {{ this.style.opacity='0.8'; }};
      btn.onclick = function(e) {{ e.stopPropagation(); overlay.remove(); }};
      overlay.onclick = function() {{ overlay.remove(); }};
      overlay.appendChild(img);
      overlay.appendChild(btn);
      window.parent.document.body.appendChild(overlay);
      function onKey(e) {{
        if (e.key==='Escape') {{ overlay.remove(); window.parent.document.removeEventListener('keydown',onKey); }}
      }}
      window.parent.document.addEventListener('keydown', onKey);
    }}
    </script>"""

    components.html(html, height=thumb_width + 40, scrolling=False)


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
            "أجب مباشرةً بالعربية فقط دون عناوين أو تنسيق إضافي. "
            "اذكر رقم الصفحة لكل معلومة بين قوسين مثل [ص.10]. "
            "إذا لم تجد الإجابة في الصفحات المرفقة، قل ذلك صراحة.\n\n"
            f"السؤال: {question}"
        )
    else:
        prompt = (
            f"Pages {page_labels} were selected by PageIndex as most relevant to the question.\n\n"
            "Instructions:\n"
            "- Answer directly in plain paragraphs. Do NOT output headers like 'Question:', 'Answer:', or any section titles.\n"
            "- Use ONLY information visible in the provided page images.\n"
            "- Cite the page label inline for every fact, e.g. [p.10].\n"
            "- If the answer is not visible in these pages, say so in one sentence.\n\n"
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


# ─── Convenience accessor ─────────────────────────────────────────────────────

def ui(key: str) -> str:
    """Return the UI string for the current demo language (or English fallback)."""
    lang = st.session_state.get("demo_lang", "en") if st.session_state.get("is_demo") else "en"
    return UI[lang].get(key, UI["en"][key])


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

    # Demo document toggle
    st.markdown(f"**{ui('sample_doc')}**")
    st.caption(ui("sample_caption"))

    col_en, col_ar = st.columns(2)
    with col_en:
        t = "primary" if (st.session_state.demo_lang == "en" and st.session_state.is_demo) else "secondary"
        if st.button("🇬🇧 English", use_container_width=True, type=t):
            load_demo("en")
            st.rerun()
    with col_ar:
        t = "primary" if (st.session_state.demo_lang == "ar" and st.session_state.is_demo) else "secondary"
        if st.button("🇸🇦 العربية", use_container_width=True, type=t):
            load_demo("ar")
            st.rerun()

    if st.session_state.is_demo:
        demo_info = DEMO_DOCS[st.session_state.demo_lang]
        st.success(f"✅ {demo_info['label']}")
        st.caption(f"{demo_info['pages']} {ui('mda_caption')}")

    st.divider()

    # Quick sample questions — always visible in sidebar when demo is active
    if st.session_state.is_demo and st.session_state.indexed:
        lang      = st.session_state.demo_lang
        questions = SAMPLE_QUESTIONS[lang]
        st.markdown(f"**{ui('quick_questions')}**")
        for q in questions:
            if st.button(q, key=f"sq_{q}", use_container_width=True):
                st.session_state["prefill_question"] = q
                st.rerun()
        st.divider()

    # Upload your own
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
                st.success(f"✅ {ui('indexed_ready')}")

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
    # Welcome card — shown only before first message
    if not st.session_state.messages and st.session_state.is_demo:
        demo_info = DEMO_DOCS[st.session_state.demo_lang]
        st.info(
            f"**{demo_info['flag']} {ui('welcome_title')}** — "
            f"_{demo_info['label']}_\n\n"
            f"{ui('welcome_body')}"
        )

    # Chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("page_images"):
                render_image_gallery(msg["page_images"])

    if not st.session_state.indexed:
        st.info(ui("upload_prompt"))


# ── Developer Dashboard tab ───────────────────────────────────────────────────

with tab_dev:

    # ── Pipeline flow diagram ─────────────────────────────────────────────────
    st.subheader("Pipeline Architecture")

    last = st.session_state.last_stats
    def step_color(ms_key):
        """Green if fast, amber if moderate, red if slow. Grey if no data."""
        if not last:
            return "#6c757d"
        ms = last.get(ms_key, 0)
        if ms < 1000:   return "#28a745"
        if ms < 3000:   return "#fd7e14"
        return "#dc3545"

    flow_html = f"""
    <div style="display:flex;align-items:center;gap:0;flex-wrap:wrap;margin:12px 0 20px;font-family:sans-serif;">
      {_flow_step("📝", "Question", "#4361ee", "")}
      {_flow_arrow()}
      {_flow_step("🔍", "PageIndex", step_color("pageindex_ms"),
                  f"{last['pageindex_ms']:.0f} ms" if last else "—")}
      {_flow_arrow()}
      {_flow_step("📄", "Page Render", step_color("render_ms"),
                  f"{last['render_ms']:.0f} ms" if last else "—")}
      {_flow_arrow()}
      {_flow_step("🤖", "Groq Vision", step_color("groq_ms"),
                  f"{last['groq_ms']:.0f} ms" if last else "—")}
      {_flow_arrow()}
      {_flow_step("💬", "Answer", "#4361ee", "")}
    </div>
    """

    # Use placeholder functions to avoid forward-reference issues — define them now
    def _flow_step(icon, label, color, timing):
        timing_html = f'<div style="font-size:11px;color:{color};font-weight:600;margin-top:3px;">{timing}</div>' if timing else ""
        return f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    background:{color}18;border:1.5px solid {color};
                    border-radius:10px;padding:10px 16px;min-width:100px;text-align:center;">
          <div style="font-size:1.4rem;">{icon}</div>
          <div style="font-size:13px;font-weight:600;color:#212529;margin-top:2px;">{label}</div>
          {timing_html}
        </div>"""

    def _flow_arrow():
        return '<div style="font-size:1.4rem;color:#adb5bd;padding:0 4px;align-self:center;">→</div>'

    # Rebuild with real functions now defined
    flow_html = f"""
    <div style="display:flex;align-items:center;gap:0;flex-wrap:wrap;margin:12px 0 20px;font-family:sans-serif;">
      {_flow_step("📝", "Question", "#4361ee", "")}
      {_flow_arrow()}
      {_flow_step("🔍", "PageIndex", step_color("pageindex_ms"),
                  f"{last['pageindex_ms']:.0f} ms" if last else "—")}
      {_flow_arrow()}
      {_flow_step("📄", "Page Render", step_color("render_ms"),
                  f"{last['render_ms']:.0f} ms" if last else "—")}
      {_flow_arrow()}
      {_flow_step("🤖", "Groq Vision", step_color("groq_ms"),
                  f"{last['groq_ms']:.0f} ms" if last else "—")}
      {_flow_arrow()}
      {_flow_step("💬", "Answer", "#4361ee", "")}
    </div>"""

    components.html(flow_html, height=110, scrolling=False)

    # ── Metric cards ──────────────────────────────────────────────────────────
    st.subheader("Last Query Metrics")
    if last:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("⏱ PageIndex",   f"{last['pageindex_ms']:.0f} ms")
        m2.metric("🖼 Page Render", f"{last['render_ms']:.0f} ms")
        m3.metric("🤖 Groq Vision", f"{last['groq_ms']:.0f} ms")
        m4.metric("⚡ Total",       f"{last['total_ms']:.0f} ms")
        m5.metric("📄 Pages Used",  len(last["pages_retrieved"]))

        d1, d2, d3 = st.columns(3)
        d1.markdown(
            f"**Question**  \n{last['question']}"
        )
        d2.markdown(
            f"**Pages retrieved**  \n`{last['pages_retrieved']}`  \n"
            f"**Images sent to Groq**  \n`{last['images_sent']}`  \n"
            f"**Detected language**  \n`{last['language']}`"
        )
        if last.get("token_usage"):
            u = last["token_usage"]
            d3.markdown(
                f"**Groq token usage**  \n"
                f"Prompt: `{u.get('prompt_tokens','?')}`  \n"
                f"Completion: `{u.get('completion_tokens','?')}`  \n"
                f"Total: `{u.get('total_tokens','?')}`"
            )

        with st.expander("📄 Raw PageIndex response"):
            st.json(st.session_state.last_raw or {})
    else:
        st.caption("No queries yet — ask a question in the Chat tab.")

    st.divider()

    # ── Active document info ──────────────────────────────────────────────────
    st.subheader("Active Document & Models")
    ci1, ci2 = st.columns(2)
    with ci1:
        st.code(
            f"Name    : {st.session_state.pdf_name or '—'}\n"
            f"Pages   : {st.session_state.total_pages or '—'}\n"
            f"Doc ID  : {st.session_state.doc_id or '—'}\n"
            f"Indexed : {st.session_state.indexed}",
            language="yaml",
        )
    with ci2:
        st.code(
            f"Vision LLM  : {VISION_MODEL}\n"
            f"Retrieval   : {PAGEINDEX_CHAT_URL}\n"
            f"Render DPI  : {RENDER_DPI}\n"
            f"Image limit : {MAX_IMAGES_PER_REQ} per request",
            language="yaml",
        )

    st.divider()

    # ── Query log ─────────────────────────────────────────────────────────────
    total_q = len(st.session_state.pipeline_log)
    st.subheader(f"Session Query Log — {total_q} {'query' if total_q == 1 else 'queries'}")
    if st.session_state.pipeline_log:
        rows = []
        for entry in reversed(st.session_state.pipeline_log):
            rows.append({
                "Time"        : entry["timestamp"],
                "Question"    : entry["question"][:60] + ("…" if len(entry["question"]) > 60 else ""),
                "Lang"        : entry["language"],
                "Pages"       : str(entry["pages_retrieved"]),
                "PI (ms)"     : f"{entry['pageindex_ms']:.0f}",
                "Render (ms)" : f"{entry['render_ms']:.0f}",
                "Groq (ms)"   : f"{entry['groq_ms']:.0f}",
                "Total (ms)"  : f"{entry['total_ms']:.0f}",
                "Tokens"      : entry.get("token_usage", {}).get("total_tokens", "—"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("Query log is empty.")


# ─── Chat input (always at page bottom) ──────────────────────────────────────

if not st.session_state.indexed:
    st.stop()

prefill  = st.session_state.pop("prefill_question", None)
question = st.chat_input(ui("chat_input")) or prefill

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with tab_chat:
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Finding relevant pages…"):
                page_nums, raw_retrieval, pi_ms = retrieve_pages(
                    st.session_state.doc_id, question
                )
            st.session_state.last_raw = raw_retrieval

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

            if not page_nums:
                pi_answer = (
                    raw_retrieval.get("choices", [{}])[0]
                                 .get("message", {})
                                 .get("content", "")
                )
                answer = (
                    pi_answer + ui("no_citations")
                    if pi_answer else ui("no_pages")
                )
                token_usage, groq_ms = {}, 0.0
            else:
                with st.spinner("Reading pages…"):
                    answer, token_usage, groq_ms = answer_from_images(
                        question, page_images, lang
                    )

            st.markdown(answer)
            if page_images:
                render_image_gallery(page_images)

    # Stats
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

    st.session_state.messages.append({
        "role"       : "assistant",
        "content"    : answer,
        "page_images": page_images,
    })
    if st.session_state.is_demo:
        lk = st.session_state.demo_lang
        st.session_state[f"messages_{lk}"]   = list(st.session_state.messages)
        st.session_state[f"page_cache_{lk}"] = dict(st.session_state.page_cache)
