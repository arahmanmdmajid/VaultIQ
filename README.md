# VaultIQ: Governed Document Intelligence

**Upload any image-based document in any language. Ask questions. Get grounded, auditable answers.**

VaultIQ is a multilingual Visual RAG platform built for enterprises. It combines vision-based document reasoning with a governed AI pipeline — so every query is traceable, every answer is cited, and every interaction is audit-logged.

Built for the **[TechEx Intelligent Enterprise Solutions Hackathon](https://lablab.ai/ai-hackathons/techex-intelligent-enterprise-solutions-hackathon/)** hosted on lablab.ai.

> **POC:** Arabic/English querying over the Madinah Tranquil Livable City 2024 report.

## What It Does

Answers natural-language questions about Madinah's urban development in both Arabic and English, grounded in the official 2024 report. The pipeline uses **Vision RAG** — rather than relying on OCR text extraction, it identifies the most relevant report pages visually and feeds those raw page images directly to a vision LLM.

This approach handles Arabic typography, tables, charts, and mixed layouts significantly better than text-based approaches.

---

## Results

| Pipeline | Approach | Effective Score |
|---|---|---|
| Spike 05 — Text RAG | PageIndex `/markdown` + Groq Llama 3.3 (text) | 81% |
| **Spike 06 — Vision RAG** | **PageIndex `/doc` + Groq Llama 4 Scout (vision)** | **93% (+12%)** |

**Vision RAG is the adopted primary pipeline.**

---

## Architecture

```
PDF file
  └─▶ PageIndex submit_document()       ← builds visual reasoning graph
         └─▶ doc_id
               └─▶ submit_query(doc_id, question)
                     └─▶ get_retrieval()
                           └─▶ relevant page numbers
                                 └─▶ load + compress PNG → JPEG
                                       └─▶ base64 encode (up to 5 pages)
                                             └─▶ Llama 4 Scout via Groq
                                                   └─▶ grounded answer
```

---

## Project Structure

```
mda-urban-intelligence/
├── notebooks/
│   ├── spike_01_pdf_extraction.ipynb   # PDF → page PNGs (PyMuPDF)
│   ├── spike_02_arabic_ocr.ipynb       # Arabic OCR via Gemini Vision
│   ├── spike_03_english_ocr.ipynb      # English OCR via Chandra
│   ├── spike_04_pageindex.ipynb        # Structural indexing via PageIndex /markdown
│   ├── spike_05_retrieval.ipynb        # Text RAG pipeline — 81% effective score
│   └── spike_06_vision_rag.ipynb       # Vision RAG pipeline — 93% effective score
├── data/
│   ├── pdfs/                           # Full PDFs (not committed — too large)
│   ├── images_en/                      # Full EN page PNGs (not committed)
│   ├── images_ar/                      # Full AR page PNGs (not committed)
│   ├── images_en_subset/               # 14 sampled EN page PNGs
│   ├── images_ar_subset/               # 14 sampled AR page PNGs
│   ├── tranquil_en_subset.pdf          # 14-page EN subset used for spiking
│   ├── tranquil_ar_subset.pdf          # 14-page AR subset used for spiking
│   ├── pageindex_structures.json       # Cached PageIndex /markdown structures
│   └── vision_doc_ids.json             # Cached PageIndex /doc doc_ids
├── ocr_output/
│   ├── english/                        # Per-page English OCR markdown files
│   └── arabic/                         # Per-page Arabic OCR markdown files
├── .env.example                        # Required environment variables
├── requirements.txt
└── README.md
```

---

## Reproducibility

### Prerequisites

- Python 3.10+
- The full EN and AR report PDFs placed at `data/pdfs/tranquil_en.pdf` and `data/pdfs/tranquil_ar.pdf`

### 1. Clone and set up the environment

```bash
git clone https://github.com/arahmanmdmajid/mda-urban-intelligence.git
cd mda-urban-intelligence

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
pip install groq pillow
```

### 2. Configure API keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```env
PAGEINDEX_API_KEY=your_pageindex_key
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key        # needed for Spike 02 (Arabic OCR)
```

| Key | Where to get it |
|---|---|
| `PAGEINDEX_API_KEY` | https://pageindex.ai |
| `GROQ_API_KEY` | https://console.groq.com |
| `GEMINI_API_KEY` | https://aistudio.google.com |

### 3. Register the Jupyter kernel

```bash
python -m ipykernel install --user --name=mda-urban-intelligence --display-name "MDA Urban Intelligence"
```

### 4. Run the spikes in order

Open Jupyter and run each notebook top-to-bottom:

```
spike_01 → spike_02 → spike_03 → spike_04 → spike_05 → spike_06
```

> **Tip:** Spikes 01–03 generate the page images and OCR outputs. If you only want to run the Vision RAG pipeline (Spike 06), you can skip Spikes 02–03 as they are only needed for the text baseline (Spike 05).

### 5. Free-tier notes

- **PageIndex**: Subset PDFs are used (14 sampled pages) to stay within upload limits
- **Groq / Llama 4 Scout**: Max 5 images per request, 4 MB per image
- **Gemini**: Only used in Spike 02 for Arabic OCR — has daily RPD limits

---

## Planned Features (Submission Scope)

- [ ] **Chat interface** — a web UI (Streamlit or Gradio) where users upload a document, type questions in Arabic or English, and receive grounded answers with page image citations
- [ ] **AI Governance layer (Lobster Trap)** — see below

---

## AI Governance — Lobster Trap

> **Lobster Trap** is a tool from one of the hackathon's sponsors and will be integrated as a governance wrapper around the completed pipeline before the demo.

**Repo:** [github.com/veeainc/lobstertrap](https://github.com/veeainc/lobstertrap)

Lobster Trap is an open-source Go-based reverse proxy that sits between the application and any LLM backend (Groq, Gemini, Ollama, or any OpenAI-compatible API). It adds a security and governance layer with zero code changes to the existing app.

```
User Query → Lobster Trap (:8080) → Groq / Llama 4 Scout → Answer
```

It inspects every prompt and response in sub-millisecond time using regex-based Deep Packet Inspection — no additional LLM calls needed for the inspection itself.

**Key features:**

| Feature | Description |
|---|---|
| PII detection | Flags SSNs, credit cards, phone numbers, official names |
| Firewall rules | iptables-style policies: ALLOW / DENY / LOG / QUARANTINE / HUMAN_REVIEW |
| Intent classification | Detects code execution attempts, file I/O, network access requests |
| Rate limiting | Requests-per-minute and burst thresholds |
| Audit logging | Full JSON log of every decision for compliance trails |

**Why it matters for this project:**

We are building a RAG system over Saudi government urban development reports. Enterprise judges care about audit trails, PII protection, and access control — not just answer quality. Lobster Trap provides all of that as a single binary added on top of the finished pipeline.

**Integration plan:** Add after all spikes pass, as a governance wrapper around the complete pipeline before the demo.

---

## Team

Built for the **TechEx Intelligent Enterprise Solutions Hackathon** on [lablab.ai](https://lablab.ai/ai-hackathons/techex-intelligent-enterprise-solutions-hackathon/).

---

## Submission Copy

### Short Description
> VaultIQ is a multilingual Visual RAG platform that lets enterprises query image-based documents in any language — with grounded, page-cited answers and a built-in AI governance layer for full auditability.

### Long Description
> Enterprises sit on vast archives of image-based documents — scanned reports, government publications, multilingual PDFs — that are impossible to query at scale. Existing tools either require clean text or work in a single language. Neither assumption holds in the real world.
>
> VaultIQ solves this with a Visual RAG pipeline: instead of extracting and indexing text, it uses **PageIndex** to build a visual reasoning graph directly from the PDF pages. When a user asks a question, PageIndex identifies which pages are relevant — then **Llama 4 Scout (via Groq)** reads those raw page images and generates a grounded answer with explicit page citations. No OCR errors. No layout destruction. Tables, charts, and non-Latin scripts are all handled natively.
>
> On top of the RAG pipeline, **Lobster Trap** acts as a governance proxy — sitting between the application and the LLM backend to enforce PII detection, firewall rules, rate limiting, and full JSON audit logging with zero code changes. Every query in, every answer out — logged, inspectable, compliant.
>
> **POC:** Arabic and English querying over the Madinah Tranquil Livable City 2024 report, achieving **93% answer accuracy** compared to 81% for a text-based baseline — a +12 percentage point improvement driven entirely by reading the pages visually.
>
> **Stack:** PageIndex · Groq (Llama 4 Scout) · Lobster Trap · Streamlit · Python
