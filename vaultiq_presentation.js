const pptxgen = require("pptxgenjs");

// ── Palette ────────────────────────────────────────────────────────────────
const NAVY    = "1B2A4A";   // primary dark
const TEAL    = "0D9488";   // accent
const TEAL_LT = "CCFBF1";   // teal light
const WHITE   = "FFFFFF";
const OFF_W   = "F8FAFC";   // light slide bg
const SLATE   = "475569";   // body text
const SLATE_L = "94A3B8";   // muted text
const CARD_BG = "FFFFFF";
const NAVY_LT = "E8EEF7";   // light navy for cards

const makeShadow = () => ({
  type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.10
});

let pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title  = "VaultIQ — Governed Document Intelligence";
pres.author = "VaultIQ Team";

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 1 — Cover
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  // Teal accent bar left edge
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: TEAL }, line: { color: TEAL } });

  // Teal decorative block bottom-right
  s.addShape(pres.shapes.RECTANGLE, { x: 7.8, y: 4.2, w: 2.2, h: 1.425, fill: { color: TEAL, transparency: 80 }, line: { color: TEAL, transparency: 80 } });
  s.addShape(pres.shapes.RECTANGLE, { x: 8.5, y: 3.5, w: 1.5, h: 1.5,   fill: { color: TEAL, transparency: 65 }, line: { color: TEAL, transparency: 65 } });

  // "VaultIQ"
  s.addText("VaultIQ", {
    x: 0.5, y: 1.1, w: 8, h: 1.3,
    fontSize: 72, bold: true, fontFace: "Calibri", color: WHITE,
    margin: 0,
  });

  // Teal divider
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 2.45, w: 2.2, h: 0.07, fill: { color: TEAL }, line: { color: TEAL } });

  // Tagline
  s.addText("Governed Document Intelligence", {
    x: 0.5, y: 2.6, w: 8, h: 0.6,
    fontSize: 26, fontFace: "Calibri", color: TEAL, margin: 0,
  });

  // Description line
  s.addText("Multilingual Visual RAG · Enterprise AI Governance · Any Document, Any Language", {
    x: 0.5, y: 3.3, w: 8.5, h: 0.45,
    fontSize: 13, fontFace: "Calibri", color: WHITE, italic: true, margin: 0,
  });

  // Hackathon badge
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.7, w: 5.6, h: 0.5,
    fill: { color: TEAL, transparency: 75 }, line: { color: TEAL, transparency: 50 }
  });
  s.addText("TechEx Intelligent Enterprise Solutions Hackathon  ·  lablab.ai", {
    x: 0.5, y: 4.7, w: 5.6, h: 0.5,
    fontSize: 12, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0,
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 2 — The Problem
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFF_W };

  s.addText("The Problem", {
    x: 0.5, y: 0.35, w: 9, h: 0.65,
    fontSize: 36, bold: true, fontFace: "Calibri", color: NAVY, margin: 0,
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.05, w: 9, h: 0.05, fill: { color: TEAL }, line: { color: TEAL } });

  s.addText("Enterprises sit on vast archives of image-based documents that are impossible to query at scale.", {
    x: 0.5, y: 1.2, w: 9, h: 0.55,
    fontSize: 15, fontFace: "Calibri", color: SLATE, italic: true, margin: 0,
  });

  const problems = [
    { icon: "📄", title: "OCR Destroys Structure", body: "Converting scanned PDFs to text breaks tables, charts, and non-Latin scripts like Arabic — the very content that matters most." },
    { icon: "🌐", title: "Single-Language Tools", body: "Most RAG solutions are English-only. Multilingual government and enterprise documents are left unqueried." },
    { icon: "🔍", title: "No Audit Trail", body: "AI answers with no source citation, no governance, and no audit log are a liability for enterprise and government use." },
  ];

  problems.forEach((p, i) => {
    const x = 0.35 + i * 3.12;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.9, w: 2.9, h: 3.15,
      fill: { color: CARD_BG }, line: { color: NAVY_LT, width: 1 },
      shadow: makeShadow(),
    });
    // Top accent
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.9, w: 2.9, h: 0.12, fill: { color: TEAL }, line: { color: TEAL } });
    // Icon
    s.addText(p.icon, {
      x: x + 0.1, y: 2.1, w: 0.7, h: 0.65,
      fontSize: 28, fontFace: "Segoe UI Emoji", margin: 0,
    });
    // Title
    s.addText(p.title, {
      x: x + 0.15, y: 2.8, w: 2.6, h: 0.65,
      fontSize: 15, bold: true, fontFace: "Calibri", color: NAVY, margin: 0,
    });
    // Body
    s.addText(p.body, {
      x: x + 0.15, y: 3.5, w: 2.6, h: 1.35,
      fontSize: 12, fontFace: "Calibri", color: SLATE, margin: 0,
    });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — Our Solution
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  s.addText("Our Solution", {
    x: 0.5, y: 0.35, w: 9, h: 0.65,
    fontSize: 36, bold: true, fontFace: "Calibri", color: WHITE, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.05, w: 9, h: 0.05, fill: { color: TEAL }, line: { color: TEAL } });

  // Left column — description
  s.addText("VaultIQ", {
    x: 0.5, y: 1.25, w: 4.4, h: 0.65,
    fontSize: 30, bold: true, fontFace: "Calibri", color: TEAL, margin: 0,
  });
  s.addText("Upload any image-based document in any language. Ask questions in Arabic or English. Get page-cited, auditable answers.", {
    x: 0.5, y: 1.95, w: 4.3, h: 1.0,
    fontSize: 14, fontFace: "Calibri", color: WHITE, margin: 0,
  });

  const points = [
    "Visual RAG — reads page images directly, no OCR errors",
    "Multilingual — Arabic, English, and beyond",
    "Page citations — every answer shows the source page",
    "Governed — full audit trail via Lobster Trap proxy",
  ];
  points.forEach((pt, i) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 3.1 + i * 0.56, w: 0.32, h: 0.32,
      fill: { color: TEAL }, line: { color: TEAL }
    });
    s.addText(pt, {
      x: 0.95, y: 3.06 + i * 0.56, w: 3.8, h: 0.5,
      fontSize: 13, fontFace: "Calibri", color: WHITE, valign: "middle", margin: 0,
    });
  });

  // Right column — POC box
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.2, w: 4.3, h: 3.9,
    fill: { color: WHITE, transparency: 7 }, line: { color: TEAL, width: 1.5 },
    shadow: makeShadow(),
  });
  s.addText("Proof of Concept", {
    x: 5.4, y: 1.4, w: 3.9, h: 0.5,
    fontSize: 16, bold: true, fontFace: "Calibri", color: TEAL, margin: 0,
  });
  s.addText("Madinah Tranquil Livable City Report 2024", {
    x: 5.4, y: 1.9, w: 3.9, h: 0.55,
    fontSize: 14, fontFace: "Calibri", color: WHITE, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.4, y: 2.55, w: 3.9, h: 0.03, fill: { color: SLATE_L }, line: { color: SLATE_L } });

  const pocRows = [
    ["Language", "Arabic + English"],
    ["Document", "Image-based PDF (112 pages)"],
    ["Pipeline", "Vision RAG (PageIndex + Llama 4 Scout)"],
    ["Governance", "Lobster Trap proxy"],
    ["Accuracy", "93% effective score"],
  ];
  pocRows.forEach(([label, val], i) => {
    s.addText(label, {
      x: 5.4, y: 2.7 + i * 0.48, w: 1.5, h: 0.44,
      fontSize: 11, bold: true, fontFace: "Calibri", color: SLATE_L, margin: 0,
    });
    s.addText(val, {
      x: 6.95, y: 2.7 + i * 0.48, w: 2.4, h: 0.44,
      fontSize: 11, fontFace: "Calibri", color: WHITE, margin: 0,
    });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 4 — How It Works
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFF_W };

  s.addText("How It Works", {
    x: 0.5, y: 0.3, w: 9, h: 0.65,
    fontSize: 36, bold: true, fontFace: "Calibri", color: NAVY, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.0, w: 9, h: 0.05, fill: { color: TEAL }, line: { color: TEAL } });

  const steps = [
    { num: "01", title: "Upload", body: "User uploads image-based PDF in any language" },
    { num: "02", title: "Index", body: "PageIndex builds a visual reasoning graph over all pages" },
    { num: "03", title: "Query", body: "User asks a question in Arabic or English" },
    { num: "04", title: "Retrieve", body: "PageIndex returns the most relevant page numbers" },
    { num: "05", title: "Answer", body: "Llama 4 Scout reads page images → grounded cited answer" },
  ];

  steps.forEach((st, i) => {
    const x = 0.3 + i * 1.88;
    // Card
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.3, w: 1.72, h: 3.6,
      fill: { color: CARD_BG }, line: { color: NAVY_LT, width: 1 },
      shadow: makeShadow(),
    });
    // Top number block
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.3, w: 1.72, h: 0.95, fill: { color: NAVY }, line: { color: NAVY } });
    s.addText(st.num, {
      x, y: 1.3, w: 1.72, h: 0.95,
      fontSize: 34, bold: true, fontFace: "Calibri", color: TEAL, align: "center", valign: "middle", margin: 0,
    });
    // Title
    s.addText(st.title, {
      x: x + 0.1, y: 2.35, w: 1.5, h: 0.55,
      fontSize: 15, bold: true, fontFace: "Calibri", color: NAVY, align: "center", margin: 0,
    });
    // Divider
    s.addShape(pres.shapes.RECTANGLE, { x: x + 0.4, y: 2.95, w: 0.92, h: 0.04, fill: { color: TEAL }, line: { color: TEAL } });
    // Body
    s.addText(st.body, {
      x: x + 0.1, y: 3.05, w: 1.52, h: 1.65,
      fontSize: 11.5, fontFace: "Calibri", color: SLATE, align: "center", margin: 0,
    });
    // Arrow (except last)
    if (i < steps.length - 1) {
      s.addText("→", {
        x: x + 1.72, y: 2.7, w: 0.16, h: 0.4,
        fontSize: 16, fontFace: "Calibri", color: TEAL, align: "center", margin: 0,
      });
    }
  });

  // Footer note
  s.addText("Governance layer: Lobster Trap sits between the app and Groq — every prompt and response is inspected, logged, and auditable.", {
    x: 0.5, y: 5.1, w: 9, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: SLATE_L, italic: true, align: "center", margin: 0,
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 5 — Results
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  s.addText("Results", {
    x: 0.5, y: 0.3, w: 9, h: 0.65,
    fontSize: 36, bold: true, fontFace: "Calibri", color: WHITE, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.0, w: 9, h: 0.05, fill: { color: TEAL }, line: { color: TEAL } });

  // Baseline card
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 1.25, w: 4.0, h: 3.75,
    fill: { color: WHITE, transparency: 8 }, line: { color: SLATE_L, width: 1 },
    shadow: makeShadow(),
  });
  s.addText("Text RAG Baseline", {
    x: 0.8, y: 1.45, w: 3.6, h: 0.5,
    fontSize: 16, bold: true, fontFace: "Calibri", color: SLATE_L, align: "center", margin: 0,
  });
  s.addText("Spike 05", {
    x: 0.8, y: 1.95, w: 3.6, h: 0.4,
    fontSize: 13, fontFace: "Calibri", color: SLATE_L, align: "center", italic: true, margin: 0,
  });
  s.addText("81%", {
    x: 0.8, y: 2.4, w: 3.6, h: 1.3,
    fontSize: 84, bold: true, fontFace: "Calibri", color: SLATE_L, align: "center", margin: 0,
  });
  s.addText("PageIndex /markdown + Groq Llama 3.3\nText passages → text answer", {
    x: 0.8, y: 3.75, w: 3.6, h: 0.9,
    fontSize: 12, fontFace: "Calibri", color: SLATE_L, align: "center", margin: 0,
  });

  // Vision card
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.4, y: 1.25, w: 4.0, h: 3.75,
    fill: { color: TEAL, transparency: 10 }, line: { color: TEAL, width: 2 },
    shadow: makeShadow(),
  });
  s.addText("✦  Vision RAG  ✦", {
    x: 5.6, y: 1.45, w: 3.6, h: 0.5,
    fontSize: 16, bold: true, fontFace: "Calibri", color: TEAL_LT, align: "center", margin: 0,
  });
  s.addText("Spike 06  ·  Adopted pipeline", {
    x: 5.6, y: 1.95, w: 3.6, h: 0.4,
    fontSize: 13, fontFace: "Calibri", color: WHITE, align: "center", italic: true, margin: 0,
  });
  s.addText("93%", {
    x: 5.6, y: 2.4, w: 3.6, h: 1.3,
    fontSize: 84, bold: true, fontFace: "Calibri", color: WHITE, align: "center", margin: 0,
  });
  s.addText("PageIndex /doc + Groq Llama 4 Scout\nPage images → cited visual answer", {
    x: 5.6, y: 3.75, w: 3.6, h: 0.9,
    fontSize: 12, fontFace: "Calibri", color: WHITE, align: "center", margin: 0,
  });

  // Delta callout
  s.addShape(pres.shapes.RECTANGLE, {
    x: 4.12, y: 2.55, w: 1.76, h: 0.85,
    fill: { color: TEAL }, line: { color: TEAL },
    shadow: makeShadow(),
  });
  s.addText("+12%", {
    x: 4.12, y: 2.55, w: 1.76, h: 0.85,
    fontSize: 28, bold: true, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0,
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 6 — AI Governance: Lobster Trap
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: OFF_W };

  s.addText("AI Governance Layer", {
    x: 0.5, y: 0.3, w: 7, h: 0.65,
    fontSize: 36, bold: true, fontFace: "Calibri", color: NAVY, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.0, w: 9, h: 0.05, fill: { color: TEAL }, line: { color: TEAL } });

  // Sponsor badge
  s.addShape(pres.shapes.RECTANGLE, {
    x: 7.4, y: 0.28, w: 2.15, h: 0.58,
    fill: { color: TEAL }, line: { color: TEAL },
    shadow: makeShadow(),
  });
  s.addText("Sponsor Tool", {
    x: 7.4, y: 0.28, w: 2.15, h: 0.58,
    fontSize: 13, bold: true, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0,
  });

  // Flow diagram
  const flow = ["Your App", "Lobster Trap :8080", "Groq / LLM Backend"];
  const flowColors = [NAVY_LT, TEAL, NAVY_LT];
  const flowText   = [NAVY,    WHITE, NAVY];
  flow.forEach((label, i) => {
    const x = 0.5 + i * 3.1;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.2, w: 2.7, h: 0.7,
      fill: { color: flowColors[i] }, line: { color: flowColors[i] },
      shadow: makeShadow(),
    });
    s.addText(label, {
      x, y: 1.2, w: 2.7, h: 0.7,
      fontSize: 14, bold: i === 1, fontFace: "Calibri", color: flowText[i], align: "center", valign: "middle", margin: 0,
    });
    if (i < flow.length - 1) {
      s.addText("→", {
        x: x + 2.7, y: 1.3, w: 0.4, h: 0.5,
        fontSize: 20, fontFace: "Calibri", color: TEAL, align: "center", margin: 0,
      });
    }
  });

  // Features grid
  const features = [
    { icon: "🔒", title: "PII Detection",       body: "Flags SSNs, credit cards, phone numbers, and official names before they reach the LLM." },
    { icon: "🛡️", title: "Firewall Rules",       body: "iptables-style policies: ALLOW / DENY / LOG / QUARANTINE / HUMAN_REVIEW." },
    { icon: "🎯", title: "Intent Classification", body: "Detects code execution, file I/O, and network access attempts in user prompts." },
    { icon: "📋", title: "Audit Logging",         body: "Full JSON log of every decision — every prompt in, every response out, timestamped." },
    { icon: "⚡", title: "Zero Latency",          body: "Sub-millisecond regex-based Deep Packet Inspection. No extra LLM calls needed." },
    { icon: "🔧", title: "Zero Code Changes",     body: "Drop-in reverse proxy. Add governance to any existing app without touching its code." },
  ];

  features.forEach((f, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.4 + col * 3.1;
    const y = 2.2 + row * 1.6;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.85, h: 1.4,
      fill: { color: CARD_BG }, line: { color: NAVY_LT, width: 1 },
      shadow: makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.08, h: 1.4, fill: { color: TEAL }, line: { color: TEAL } });
    s.addText(f.icon + "  " + f.title, {
      x: x + 0.18, y: y + 0.1, w: 2.55, h: 0.42,
      fontSize: 13, bold: true, fontFace: "Calibri", color: NAVY, margin: 0,
    });
    s.addText(f.body, {
      x: x + 0.18, y: y + 0.54, w: 2.55, h: 0.80,
      fontSize: 11, fontFace: "Calibri", color: SLATE, margin: 0,
    });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 7 — Tech Stack
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  s.addText("Tech Stack", {
    x: 0.5, y: 0.3, w: 9, h: 0.65,
    fontSize: 36, bold: true, fontFace: "Calibri", color: WHITE, margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.0, w: 9, h: 0.05, fill: { color: TEAL }, line: { color: TEAL } });

  const techs = [
    { name: "PageIndex",         role: "Visual PDF reasoning graph\n& page-level retrieval",   sponsor: true  },
    { name: "Groq",              role: "Ultra-fast LLM inference\nplatform",                   sponsor: true  },
    { name: "Lobster Trap",      role: "AI governance & security\nreverse proxy",              sponsor: true  },
    { name: "Llama 4 Scout",     role: "Vision LLM — reads page\nimages & generates answers", sponsor: false },
    { name: "PyMuPDF + Pillow",  role: "PDF-to-image rendering\n& compression",               sponsor: false },
    { name: "Streamlit",         role: "Chat interface for\ndocument Q&A",                     sponsor: false },
  ];

  techs.forEach((t, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x   = 0.4 + col * 3.1;
    const y   = 1.25 + row * 2.05;

    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 2.85, h: 1.8,
      fill: { color: WHITE, transparency: t.sponsor ? 0 : 12 },
      line: { color: t.sponsor ? TEAL : SLATE_L, width: t.sponsor ? 2 : 1 },
      shadow: makeShadow(),
    });

    if (t.sponsor) {
      s.addShape(pres.shapes.RECTANGLE, { x: x + 1.9, y, w: 0.95, h: 0.38, fill: { color: TEAL }, line: { color: TEAL } });
      s.addText("Sponsor", {
        x: x + 1.9, y, w: 0.95, h: 0.38,
        fontSize: 10, bold: true, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0,
      });
    }

    s.addText(t.name, {
      x: x + 0.15, y: y + 0.45, w: 2.55, h: 0.55,
      fontSize: 17, bold: true, fontFace: "Calibri", color: t.sponsor ? NAVY : WHITE, margin: 0,
    });
    s.addText(t.role, {
      x: x + 0.15, y: y + 1.0, w: 2.55, h: 0.72,
      fontSize: 12, fontFace: "Calibri", color: t.sponsor ? SLATE : SLATE_L, margin: 0,
    });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 8 — Thank You / CTA
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: TEAL }, line: { color: TEAL } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.2, w: 10, h: 1.425, fill: { color: WHITE, transparency: 94 }, line: { color: WHITE, transparency: 94 } });

  s.addText("Thank You", {
    x: 0.5, y: 0.85, w: 9, h: 1.25,
    fontSize: 64, bold: true, fontFace: "Calibri", color: WHITE, align: "center", margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.5, y: 2.05, w: 3.0, h: 0.07, fill: { color: TEAL }, line: { color: TEAL } });
  s.addText("VaultIQ — Governed Document Intelligence", {
    x: 0.5, y: 2.2, w: 9, h: 0.55,
    fontSize: 20, fontFace: "Calibri", color: TEAL, align: "center", margin: 0,
  });

  s.addText("Multilingual  ·  Visual RAG  ·  Enterprise-Grade Governance", {
    x: 0.5, y: 2.85, w: 9, h: 0.45,
    fontSize: 14, fontFace: "Calibri", color: WHITE, align: "center", italic: true, margin: 0,
  });

  s.addText("github.com/arahmanmdmajid/mda-urban-intelligence", {
    x: 0.5, y: 4.25, w: 9, h: 0.45,
    fontSize: 13, fontFace: "Calibri", color: SLATE_L, align: "center", margin: 0,
  });
  s.addText("TechEx Intelligent Enterprise Solutions Hackathon  ·  lablab.ai", {
    x: 0.5, y: 4.75, w: 9, h: 0.4,
    fontSize: 12, fontFace: "Calibri", color: SLATE_L, align: "center", margin: 0,
  });
}

// ── Write file ──────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "C:/Dev/mda-urban-intelligence/VaultIQ_Presentation.pptx" })
  .then(() => console.log("✅ VaultIQ_Presentation.pptx saved"))
  .catch(err => { console.error("❌", err); process.exit(1); });
