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


def _active_pi_key() -> str:
    """Return the PageIndex API key to use: user-supplied key takes priority."""
    return (
        st.session_state.get("user_pi_key")
        or os.getenv("PAGEINDEX_API_KEY")
        or ""
    )


def retrieve_pages(doc_id: str, question: str) -> tuple[list[int], dict, float]:
    payload = {
        "doc_id"          : doc_id,
        "messages"        : [{"role": "user", "content": question}],
        "stream"          : False,
        "enable_citations": True,
    }
    headers = {
        "api_key"     : _active_pi_key(),
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


def retrieve_pages_fallback(
    pdf_bytes: bytes, question: str, total_pages: int
) -> tuple[list[int], float]:
    """
    Text-based fallback retrieval used when PageIndex is unavailable.
    Extracts page text via PyMuPDF and asks a fast Groq text model which
    pages are most relevant to the question.  Returns (page_nums, elapsed_ms).
    """
    import json

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    excerpts = []
    for i in range(min(total_pages, 20)):
        text = doc[i].get_text("text").strip()[:700]
        if text:
            excerpts.append(f"[Page {i + 1}]: {text}")
    doc.close()

    if not excerpts:
        return [], 0.0

    prompt = (
        "You are a document retrieval assistant.\n"
        "Identify which pages of the document are most relevant to the user's question.\n"
        "Return ONLY a valid JSON array of page numbers (integers), e.g. [3, 7, 12].\n"
        "Select at most 5 pages. Return [] if no pages are clearly relevant.\n\n"
        f"Question: {question}\n\n"
        "Page excerpts:\n" + "\n\n".join(excerpts)
    )

    t0       = time.perf_counter()
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    elapsed = (time.perf_counter() - t0) * 1000

    content = response.choices[0].message.content.strip()
    try:
        m     = re.search(r"\[[\d\s,]+\]", content)
        pages = json.loads(m.group(0)) if m else []
        return sorted(set(p for p in pages if 1 <= p <= total_pages)), elapsed
    except Exception:
        return [], elapsed


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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --cyan: #0d7494;
    --cyan-dim: rgba(13, 116, 148, 0.10);
    --green: #0f7a5a;
    --green-dim: rgba(15, 122, 90, 0.12);
    --amber: #b45309;
    --amber-dim: rgba(180, 83, 9, 0.10);
    --red: #b91c1c;
    --red-dim: rgba(185, 28, 28, 0.10);
    --grey: #6b7280;
    --border: #e5e7eb;
    --bg-subtle: #f9fafb;
    --font-main: 'Inter', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', 'Consolas', monospace;
    --radius: 10px;
}

.stChatMessage p { font-size: 0.95rem; line-height: 1.6; }

/* ── Developer dashboard ── */
.dev-section { margin: 0 0 1.5rem; }
.dev-section-title {
    font-family: var(--font-main);
    font-size: 0.70rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--grey);
    margin: 0 0 0.6rem;
}

/* Pipeline step rows */
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 14px;
    border-radius: var(--radius);
    background: var(--bg-subtle);
    border: 1px solid var(--border);
    margin-bottom: 7px;
    font-family: var(--font-main);
}
.dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-green { background: #0f7a5a; box-shadow: 0 0 0 3px rgba(15,122,90,0.18); }
.dot-amber { background: #b45309; box-shadow: 0 0 0 3px rgba(180,83,9,0.18); }
.dot-red   { background: #b91c1c; box-shadow: 0 0 0 3px rgba(185,28,28,0.18); }
.dot-grey  { background: #9ca3af; }
.dot-cyan  { background: #0d7494; box-shadow: 0 0 0 3px rgba(13,116,148,0.18); }
.step-name   { font-size: 0.875rem; font-weight: 600; color: #111827; flex: 1; }
.step-detail { font-size: 0.80rem; color: #6b7280; font-family: var(--font-main); }
.step-badge  {
    font-family: var(--font-mono);
    font-size: 0.74rem;
    padding: 2px 9px;
    border-radius: 5px;
    background: rgba(13,116,148,0.10);
    color: #0d7494;
    font-weight: 500;
    white-space: nowrap;
    flex-shrink: 0;
}

/* Timing pills */
.timing-pill {
    padding: 12px 16px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: var(--bg-subtle);
    margin-bottom: 10px;
    font-family: var(--font-main);
}
.timing-pill-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 7px;
}
.timing-pill-name  { font-size: 0.875rem; font-weight: 600; color: #111827; }
.timing-pill-value { font-size: 1.05rem; font-weight: 700; color: #0d7494; font-family: var(--font-mono); }
.timing-bar-bg     { height: 6px; border-radius: 3px; background: var(--border); overflow: hidden; }
.timing-bar-fill   { height: 100%; border-radius: 3px; background: #0d7494; }

/* Model badge (larger, standalone) */
.model-badge {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    padding: 0.25em 0.75em;
    border-radius: 6px;
    background: rgba(13,116,148,0.10);
    color: #0d7494;
    font-weight: 500;
    display: inline-block;
}

/* Health rows */
.health-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 0;
    border-bottom: 1px solid var(--border);
    font-family: var(--font-main);
    font-size: 0.875rem;
}
.health-row:last-child { border-bottom: none; }
.health-label { flex: 1; color: #374151; }
.health-ok    { color: #0f7a5a; font-weight: 600; }
.health-err   { color: #b91c1c; font-weight: 600; }
.health-na    { color: #6b7280; font-weight: 600; }
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

    # PageIndex API key — lets users supply their own key if the app quota is exhausted
    with st.expander("🔑 PageIndex API key"):
        key_input = st.text_input(
            "Your PageIndex key",
            value=st.session_state.get("user_pi_key", ""),
            type="password",
            placeholder="pi-…",
            label_visibility="collapsed",
            help="Used only for PageIndex retrieval calls this session. Never stored.",
        )
        if key_input != st.session_state.get("user_pi_key", ""):
            st.session_state["user_pi_key"] = key_input.strip() or None
            st.rerun()

        if st.session_state.get("user_pi_key"):
            st.success("✓ Custom key active", icon="🔑")
        elif os.getenv("PAGEINDEX_API_KEY"):
            st.caption("Using app-level key.")
        else:
            st.warning("No PageIndex key — fallback retrieval active.", icon="⚠️")

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
    last = st.session_state.last_stats

    # ── Shared helpers ────────────────────────────────────────────────────────

    def dot_color(ms):
        """Map latency in ms to a CSS dot colour name."""
        if ms is None: return "grey"
        if ms < 1000:  return "green"
        if ms < 3000:  return "amber"
        return "red"

    def step_row(dot, name, detail="", badge=None):
        """Return an HTML pipeline-step row string."""
        badge_html = f'<span class="step-badge">{badge}</span>' if badge else ""
        return (
            f'<div class="pipeline-step">'
            f'<div class="dot dot-{dot}"></div>'
            f'<span class="step-name">{name}</span>'
            f'<span class="step-detail">{detail}</span>'
            f'{badge_html}'
            f'</div>'
        )

    def timing_pill(name, ms, total_ms):
        """Return an HTML timing-pill string with a proportional progress bar."""
        pct = min(int((ms / total_ms) * 100), 100) if total_ms else 0
        return (
            f'<div class="timing-pill">'
            f'<div class="timing-pill-header">'
            f'<span class="timing-pill-name">{name}</span>'
            f'<span class="timing-pill-value">{ms:.0f} ms</span>'
            f'</div>'
            f'<div class="timing-bar-bg">'
            f'<div class="timing-bar-fill" style="width:{pct}%"></div>'
            f'</div>'
            f'<div style="font-size:0.70rem;color:#9ca3af;margin-top:4px;">{pct}% of total</div>'
            f'</div>'
        )

    # ── 5 sub-tabs ────────────────────────────────────────────────────────────

    sub_status, sub_timings, sub_raw, sub_rag, sub_models = st.tabs([
        "⚡ Pipeline Status",
        "⏱ Timings",
        "📄 Raw JSON",
        "🔍 Vision RAG Debug",
        "🤖 Models",
    ])

    # ── Pipeline Status ───────────────────────────────────────────────────────
    with sub_status:
        pi_ms_v     = last["pageindex_ms"] if last else None
        render_ms_v = last["render_ms"]    if last else None
        groq_ms_v   = last["groq_ms"]      if last else None
        total_ms_v  = last["total_ms"]     if last else None

        q_text      = last["question"] if last else "—"
        q_short     = (q_text[:72] + "…") if len(q_text) > 72 else q_text

        pi_detail     = f"{pi_ms_v:.0f} ms"    if pi_ms_v     is not None else "waiting…"
        render_detail = (
            f"{render_ms_v:.0f} ms · {last['images_sent']} image(s)" if last else "waiting…"
        )
        groq_detail   = f"{groq_ms_v:.0f} ms"  if groq_ms_v   is not None else "waiting…"
        total_detail  = f"{total_ms_v:.0f} ms end-to-end" if total_ms_v is not None else "waiting…"

        steps_html = (
            '<div class="dev-section">'
            '<div class="dev-section-title">Pipeline Steps — Last Query</div>'
            + step_row("cyan",                    "1 · User Question",      q_short)
            + step_row(dot_color(pi_ms_v),        "2 · PageIndex Retrieval", pi_detail,     "chat-completion API")
            + step_row(dot_color(render_ms_v),    "3 · Page Rendering",      render_detail, f"DPI {RENDER_DPI}")
            + step_row(dot_color(groq_ms_v),      "4 · Groq Vision LLM",    groq_detail,   "Llama 4 Scout")
            + step_row("cyan",                    "5 · Answer Delivered",    total_detail)
            + '</div>'
        )
        st.markdown(steps_html, unsafe_allow_html=True)

        if not last:
            st.info("No queries yet — ask a question in the Chat tab to populate pipeline data.")
        else:
            total_q = len(st.session_state.pipeline_log)
            st.markdown(f"---")
            st.markdown(f"**Session summary** — {total_q} {'query' if total_q == 1 else 'queries'} this session")
            rows = []
            for entry in reversed(st.session_state.pipeline_log):
                rows.append({
                    "Time"       : entry["timestamp"],
                    "Question"   : entry["question"][:55] + ("…" if len(entry["question"]) > 55 else ""),
                    "Lang"       : entry["language"],
                    "Pages"      : str(entry["pages_retrieved"]),
                    "PI (ms)"    : f"{entry['pageindex_ms']:.0f}",
                    "Render (ms)": f"{entry['render_ms']:.0f}",
                    "Groq (ms)"  : f"{entry['groq_ms']:.0f}",
                    "Total (ms)" : f"{entry['total_ms']:.0f}",
                    "Tokens"     : entry.get("token_usage", {}).get("total_tokens", "—"),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

    # ── Timings ───────────────────────────────────────────────────────────────
    with sub_timings:
        if last:
            pi_ms_v     = last["pageindex_ms"]
            render_ms_v = last["render_ms"]
            groq_ms_v   = last["groq_ms"]
            total_ms_v  = last["total_ms"]

            pills_html = (
                '<div class="dev-section">'
                '<div class="dev-section-title">Latency Breakdown — Last Query</div>'
                + timing_pill("PageIndex Retrieval", pi_ms_v,     total_ms_v)
                + timing_pill("Page Rendering",      render_ms_v, total_ms_v)
                + timing_pill("Groq Vision LLM",     groq_ms_v,   total_ms_v)
                + '</div>'
                + f'<div class="timing-pill" style="border-color:#0d7494;background:rgba(13,116,148,0.08);">'
                + f'<div class="timing-pill-header">'
                + f'<span class="timing-pill-name" style="color:#0d7494;">Total End-to-End</span>'
                + f'<span class="timing-pill-value">{total_ms_v:.0f} ms</span>'
                + f'</div></div>'
            )
            st.markdown(pills_html, unsafe_allow_html=True)

            if last.get("token_usage"):
                u = last["token_usage"]
                st.markdown("---")
                tokens_html = (
                    '<div class="dev-section">'
                    '<div class="dev-section-title">Groq Token Usage</div>'
                    + step_row("cyan",  "Prompt tokens",     "", str(u.get("prompt_tokens",     "?")))
                    + step_row("green", "Completion tokens", "", str(u.get("completion_tokens", "?")))
                    + step_row("cyan",  "Total tokens",      "", str(u.get("total_tokens",      "?")))
                    + '</div>'
                )
                st.markdown(tokens_html, unsafe_allow_html=True)
        else:
            st.info("No queries yet — timing data will appear here after the first question.")

    # ── Raw JSON ──────────────────────────────────────────────────────────────
    with sub_raw:
        st.markdown("**Raw PageIndex chat-completion response**")
        st.caption("Full API response payload from the last query — citations, usage, and metadata.")
        st.json(st.session_state.last_raw or {"info": "No query run yet."})

    # ── Vision RAG Debug ──────────────────────────────────────────────────────
    with sub_rag:
        if last:
            pages_ok  = bool(last["pages_retrieved"])
            images_ok = last["images_sent"] > 0

            rag_html = (
                '<div class="dev-section">'
                '<div class="dev-section-title">Retrieval Details — Last Query</div>'
                + step_row("cyan",
                           "Question", last["question"])
                + step_row("green" if pages_ok  else "red",
                           "Pages retrieved",    "",
                           str(last["pages_retrieved"]) if pages_ok else "none — no citations returned")
                + step_row("green" if images_ok else "grey",
                           "Images sent to Groq", "",
                           f"{last['images_sent']} / {MAX_IMAGES_PER_REQ} max")
                + step_row("cyan",
                           "Detected language", "",
                           "Arabic (ar)" if last["language"] == "ar" else "English (en)")
                + step_row("cyan",
                           "Document",
                           f"{st.session_state.pdf_name} · {st.session_state.total_pages} pages")
                + step_row("grey",
                           "PageIndex doc_id",
                           st.session_state.doc_id or "—")
                + '</div>'
            )
            st.markdown(rag_html, unsafe_allow_html=True)

            cache_count = len(st.session_state.page_cache)
            st.markdown(f"**Page render cache** — {cache_count} page(s) cached this session")
            if cache_count:
                st.caption(f"Cached pages: {sorted(st.session_state.page_cache.keys())}")
        else:
            st.info("No queries yet — RAG debug data will appear here after the first question.")

    # ── Models ────────────────────────────────────────────────────────────────
    with sub_models:
        groq_ok = bool(os.getenv("GROQ_API_KEY"))
        pi_ok   = bool(os.getenv("PAGEINDEX_API_KEY"))
        indexed = st.session_state.indexed

        health_html = (
            '<div class="dev-section">'
            '<div class="dev-section-title">System Health</div>'
            '<div class="health-row"><span class="health-label">Groq API key</span>'
            + ('<span class="health-ok">✓ configured</span>' if groq_ok else '<span class="health-err">✗ missing</span>')
            + '</div>'
            '<div class="health-row"><span class="health-label">PageIndex API key</span>'
            + ('<span class="health-ok">✓ configured</span>' if pi_ok else '<span class="health-err">✗ missing</span>')
            + '</div>'
            '<div class="health-row"><span class="health-label">Document indexed</span>'
            + ('<span class="health-ok">✓ ready</span>' if indexed else '<span class="health-na">— not yet</span>')
            + '</div>'
            f'<div class="health-row">'
            f'<span class="health-label">Page render cache</span>'
            f'<span class="health-ok">{len(st.session_state.page_cache)} page(s)</span>'
            f'</div>'
            '</div>'
        )

        models_html = (
            '<div class="dev-section">'
            '<div class="dev-section-title">Active Models</div>'
            + step_row("cyan", "Vision LLM",           "", VISION_MODEL)
            + step_row("cyan", "Retrieval",            "", "PageIndex Visual Reasoning")
            + step_row("grey", "Render DPI",           "", f"JPEG · {RENDER_DPI} DPI")
            + step_row("grey", "Max images / request", "", str(MAX_IMAGES_PER_REQ))
            + '</div>'
        )

        pdf_name = st.session_state.pdf_name or "—"
        doc_html = (
            '<div class="dev-section">'
            '<div class="dev-section-title">Active Document</div>'
            + step_row("cyan" if indexed else "grey",
                       pdf_name,
                       f"{st.session_state.total_pages} pages")
            + step_row("grey", "doc_id", st.session_state.doc_id or "—")
            + '</div>'
        )

        # Render health + models; doc on right
        col_health, col_models = st.columns(2)
        with col_health:
            st.markdown(health_html + doc_html, unsafe_allow_html=True)
        with col_models:
            st.markdown(models_html, unsafe_allow_html=True)


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

            # ── Automatic fallback when PageIndex is unavailable ──────────────
            # Detected via API errors (InsufficientCredits, auth failures, etc.)
            # or a completely empty response with no choices array.
            pi_api_error = (
                "detail" in raw_retrieval        # e.g. {"detail": "InsufficientCredits"}
                or "error" in raw_retrieval
                or not raw_retrieval.get("choices")
            )
            fallback_used = False
            if pi_api_error and st.session_state.pdf_bytes:
                with st.spinner("Retrieval via local text index…"):
                    page_nums, pi_ms = retrieve_pages_fallback(
                        st.session_state.pdf_bytes,
                        question,
                        st.session_state.total_pages,
                    )
                fallback_used = True

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

            if fallback_used:
                answer += (
                    "\n\n_⚠️ PageIndex unavailable (quota) — pages selected via "
                    "local text extraction. Visual accuracy may be slightly lower._"
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
