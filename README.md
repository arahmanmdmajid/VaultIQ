# VaultIQ: Governed Document Intelligence

**Upload any image-based document in any language. Ask questions. Get grounded, auditable answers.**

VaultIQ is a multilingual Visual RAG platform built for enterprises. It combines vision-based document reasoning with a governed AI pipeline — so every query is traceable, every answer is cited, and every interaction is audit-logged.

Built for the **[TechEx Intelligent Enterprise Solutions Hackathon](https://lablab.ai/ai-hackathons/techex-intelligent-enterprise-solutions-hackathon/)** hosted on lablab.ai.

> **POC:** Arabic/English querying over the Madinah Tranquil Livable City 2024 report.

---

## What It Does

Answers natural-language questions about uploaded documents in **Arabic and English**, with every answer grounded in the specific source pages. The pipeline uses **Vision RAG** — rather than relying on OCR text extraction, it identifies the most relevant report pages visually and feeds those raw page images directly to a vision LLM.

This approach handles Arabic typography, tables, charts, and mixed layouts significantly better than text-based approaches.

---

## Architecture

```
User Question
  └─▶ Streamlit app
        └─▶ Lobster Trap (:8080)          ← AI governance proxy
              │   ├─ Ingress rules (DENY / HUMAN_REVIEW / LOG)
              │   ├─ Rate limiting
              │   └─ Audit log (audit.jsonl)
              └─▶ PageIndex Chat API       ← visual reasoning graph
                    └─▶ page citations (<doc=...;page=N>)
                          └─▶ PyMuPDF render → JPEG (up to 5 pages)
                                └─▶ Groq Llama 4 Scout (vision)
                                      └─▶ grounded answer with page citations
```

---

## Project Structure

```
VaultIQ/
├── app.py                                # Streamlit chat app (main entry point)
├── lobstertrap/
│   ├── policy.yaml                       # AI governance policy (ingress + egress rules)
│   ├── start.bat                         # Windows: start the proxy
│   └── start.sh                          # macOS/Linux: start the proxy
├── data/
│   ├── tranquil_en_subset.pdf            # 14-page EN subset (pre-indexed demo doc)
│   ├── tranquil_ar_subset.pdf            # 14-page AR subset (pre-indexed demo doc)
│   ├── vision_doc_ids.json               # Cached PageIndex doc_ids for demo docs
│   └── pageindex_structures.json         # Cached PageIndex markdown structures
├── .env.example                          # Required environment variables
├── requirements.txt
└── README.md
```

---

## Running the App

### Prerequisites

- Python 3.10+
- Go 1.22+ (only needed to build the Lobster Trap binary — see below)

### 1. Clone and set up the environment

```bash
git clone https://github.com/arahmanmdmajid/VaultIQ.git
cd VaultIQ

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

```env
PAGEINDEX_API_KEY=your_pageindex_key
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key    # only needed for Spike 02 (Arabic OCR)
```

| Key | Where to get it |
|---|---|
| `PAGEINDEX_API_KEY` | https://pageindex.ai |
| `GROQ_API_KEY` | https://console.groq.com |
| `GEMINI_API_KEY` | https://aistudio.google.com |

### 3. (Optional) Start Lobster Trap

Lobster Trap is the AI governance proxy. The app works without it (falls back to direct Groq calls), but the governance features — PII detection, firewall rules, rate limiting, and audit logging — are only active when it is running.

**Build from source (one-time):**

```bash
git clone https://github.com/veeainc/lobstertrap /tmp/lt
cd /tmp/lt

# Windows:
make build-windows
copy lobstertrap.exe path\to\VaultIQ\lobstertrap\

# macOS/Linux:
make build
cp lobstertrap path/to/VaultIQ/lobstertrap/
```

**Start the proxy:**

```bash
# Windows:
lobstertrap\start.bat

# macOS/Linux:
lobstertrap/start.sh
```

The proxy starts on `http://localhost:8080` with the policy in `lobstertrap/policy.yaml`.

### 4. Run the Streamlit app

```bash
streamlit run app.py
```

Open `http://localhost:8501`. The app auto-detects whether Lobster Trap is running and shows a **🛡️ Governed** or **⚪ Direct API** badge accordingly.

A pre-indexed demo document is loaded on startup — just start asking questions.

---

## App Features

- **Bilingual chat** — ask in Arabic or English; language is auto-detected
- **Pre-loaded demo doc** — Madinah Tranquil Livable City 2024 report, both EN and AR, ready to query with no upload needed
- **Page image citations** — every answer shows thumbnail previews of the source pages with a click-to-expand lightbox
- **Document upload** — upload your own PDF; it will be indexed by PageIndex and ready to query in ~30s
- **Fallback retrieval** — if PageIndex is unavailable (quota), local text extraction via PyMuPDF keeps the app functional
- **Developer Dashboard** — pipeline timings, raw PageIndex JSON, Vision RAG debug info, and the live governance audit log
- **Governance denial cards** — when Lobster Trap blocks a query, a styled red card shows the policy message in the chat

---

## AI Governance — Lobster Trap

**Repo:** [github.com/veeainc/lobstertrap](https://github.com/veeainc/lobstertrap)

Lobster Trap is an open-source Go-based reverse proxy that sits between the application and any OpenAI-compatible LLM backend. It inspects every prompt and response and enforces a declarative YAML policy with zero changes to application code.

```
Streamlit app → Lobster Trap (:8080) → Groq API
```

### Active Policy (`lobstertrap/policy.yaml`)

| Priority | Rule | Action | Condition |
|---|---|---|---|
| 100 | `block_prompt_injection` | **DENY** | Injection patterns detected |
| 90 | `block_code_execution_intent` | **DENY** | Intent = `code_execution` |
| 89 | `block_system_command_intent` | **DENY** | Intent = `system` |
| 85 | `flag_high_risk_queries` | **HUMAN_REVIEW** | Risk score > 0.35 |
| 80 | `log_pii_in_query` | LOG | PII detected in prompt |
| 60 | `log_queries_with_urls` | LOG | URLs detected in prompt |
| — | `log_pii_in_response` | LOG (egress) | PII detected in response |
| — | `log_credentials_in_response` | LOG (egress) | Credentials detected in response |

Rate limits: **30 req/min · 200 req/hr · burst 10**

### Tested Governance Behaviours

| Query type | Result |
|---|---|
| Normal question about the document | ✅ Passes through, logged |
| `Ignore all previous instructions…` | 🛑 DENY — injection blocked |
| `Write a Python script to delete files…` | ⚠️ HUMAN_REVIEW flagged (risk 0.36) |
| Query containing PII | 📋 LOG — passes through with audit entry |

### Why it matters

We are building a RAG system over Saudi government urban development reports. Enterprise judges care about audit trails, PII protection, and access control — not just answer quality. Lobster Trap provides all of that as a single binary on top of the finished pipeline.

---

## Team — Nexus Warden

*"Connecting intelligence to action — with governance at every layer."*

| Member |
|---|
| Abdur Rahman Muhammad Abdul Majid |
| Muhammad Abdul Hadi Muhammad Abdul Majid |
| Hamayl Zahid |
| Abdul Aziz Muhammad Abdul Majid |
| Muhammad Abdullah |

Built for the **TechEx Intelligent Enterprise Solutions Hackathon** on [lablab.ai](https://lablab.ai/ai-hackathons/techex-intelligent-enterprise-solutions-hackathon/).

---

## Submission Copy

### Short Description
> VaultIQ is a multilingual Visual RAG platform that lets enterprises query image-based documents in Arabic or English — with grounded, page-cited answers and a built-in AI governance layer for full auditability.

### Long Description
> Enterprises sit on vast archives of image-based documents — scanned reports, government publications, multilingual PDFs — that are impossible to query at scale. Existing tools either require clean text or work in a single language. Neither assumption holds in the real world.
>
> VaultIQ solves this with a Visual RAG pipeline: instead of extracting and indexing text, it uses **PageIndex** to build a visual reasoning graph directly from the PDF pages. When a user asks a question, PageIndex identifies which pages are relevant — then **Llama 4 Scout (via Groq)** reads those raw page images and generates a grounded answer with explicit page citations. No OCR errors. No layout destruction. Tables, charts, and Arabic typography are all handled natively.
>
> On top of the RAG pipeline, **Lobster Trap** acts as a governance proxy — sitting between the application and the LLM backend to enforce PII detection, firewall rules, rate limiting, and full JSON audit logging. Prompt injection attempts are blocked outright. High-risk queries are flagged for human review. Every interaction is logged. Enterprise-grade auditability, out of the box.
>
> **POC:** Arabic and English querying over the Madinah Tranquil Livable City 2024 report, achieving **93% answer accuracy** vs. 81% for a text-based baseline — a +12 percentage point improvement driven entirely by reading the pages visually.
>
> **Stack:** PageIndex · Groq (Llama 4 Scout) · Lobster Trap · Streamlit · Python
