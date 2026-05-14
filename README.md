# MDA Urban Intelligence

A bilingual Arabic/English RAG (Retrieval-Augmented Generation) pipeline for querying the **Madinah Tranquil Livable City 2024** report.

Built for the **[TechEx Intelligent Enterprise Solutions Hackathon](https://lablab.ai/ai-hackathons/techex-intelligent-enterprise-solutions-hackathon/)** hosted on lablab.ai — focused on delivering enterprise-grade AI solutions for real-world government and business challenges.

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

## Planned Features

- [ ] **Full report indexing** — upload the complete 112-page PDF to PageIndex instead of the 14-page subset
- [ ] **Chat interface** — a simple web UI (Streamlit or Gradio) where users can type questions in Arabic or English and receive grounded answers with page citations
- [ ] **Source highlighting** — display the actual page image alongside the answer so the user can verify the cited content visually
- [ ] **Multi-turn conversation** — maintain chat history so follow-up questions reference earlier answers
- [ ] **Hybrid retrieval** — combine PageIndex visual retrieval with keyword fallback for questions that target specific numbers or names
- [ ] **Evaluation dashboard** — automated scoring against a curated question set to track pipeline quality as we iterate
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
