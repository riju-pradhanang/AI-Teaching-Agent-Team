/**
 * generate_docx.js
 * 
 * Called by tools/doc_generator.py via subprocess.
 * Reads JSON from stdin: { title, agent, content, date }
 * Writes .docx bytes to stdout.
 * 
 * content uses markdown-like structure:
 *   ## Heading  →  Heading2
 *   ### Heading →  Heading3
 *   - item      →  bullet list
 *   1. item     →  numbered list
 *   **bold**    →  bold run
 *   plain text  →  Normal paragraph
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Header, Footer, TabStopType, TabStopPosition,
  VerticalAlign, UnderlineType
} = require('docx');
const fs = require('fs');

// ── Read stdin ────────────────────────────────────────────────────────────
let inputData = '';
process.stdin.on('data', chunk => inputData += chunk);
process.stdin.on('end', () => {
  try {
    const { title, agent, content, date } = JSON.parse(inputData);
    buildDoc(title, agent, content, date);
  } catch (e) {
    process.stderr.write('JSON parse error: ' + e.message + '\n');
    process.exit(1);
  }
});

// ── Colour palette ────────────────────────────────────────────────────────
const AGENT_COLORS = {
  professor: { primary: "1B3A6B", accent: "2E5FA3", light: "D6E4F7", icon: "🎓" },
  advisor:   { primary: "155724", accent: "1E7E34", light: "D4EDDA", icon: "🗺️" },
  librarian: { primary: "4A235A", accent: "6C3483", light: "E8D5F5", icon: "📚" },
  ta:        { primary: "7D3C00", accent: "B45309", light: "FFF3CD", icon: "✏️" },
  unknown:   { primary: "1B2A4A", accent: "4A4A4A", light: "F2F4F7", icon: "🤖" },
};

const AGENT_LABELS = {
  professor: "Professor Nova",
  advisor:   "Advisor Sage",
  librarian: "Librarian Lumen",
  ta:        "TA Atlas",
  unknown:   "AI Teaching Team",
};

// ── Borders ───────────────────────────────────────────────────────────────
const border = (color = "CCCCCC") => ({ style: BorderStyle.SINGLE, size: 1, color });
const allBorders = (color = "CCCCCC") => ({
  top: border(color), bottom: border(color),
  left: border(color), right: border(color)
});
const noBorders = () => ({
  top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
});

// ── Inline markdown parser ────────────────────────────────────────────────
function parseInline(text, defaultColor = "2D2D2D") {
  const runs = [];
  const pattern = /\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`/g;
  let last = 0, m;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) {
      runs.push(new TextRun({ text: text.slice(last, m.index), font: "Arial", size: 22, color: defaultColor }));
    }
    if (m[1] !== undefined) {
      runs.push(new TextRun({ text: m[1], bold: true, font: "Arial", size: 22, color: defaultColor }));
    } else if (m[2] !== undefined) {
      runs.push(new TextRun({ text: m[2], italics: true, font: "Arial", size: 22, color: defaultColor }));
    } else if (m[3] !== undefined) {
      runs.push(new TextRun({ text: m[3], font: "Courier New", size: 20, color: "2D2D2D",
        shading: { fill: "F0F0F0", type: ShadingType.CLEAR } }));
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    runs.push(new TextRun({ text: text.slice(last), font: "Arial", size: 22, color: defaultColor }));
  }
  return runs.length ? runs : [new TextRun({ text, font: "Arial", size: 22, color: defaultColor })];
}

// ── Content parser ────────────────────────────────────────────────────────
function parseContent(content, colors) {
  const paras = [];
  const lines = content.split('\n');
  let inCode = false;
  let codeLines = [];

  const flushCode = () => {
    if (codeLines.length === 0) return;
    codeLines.forEach(cl => {
      paras.push(new Paragraph({
        children: [new TextRun({ text: cl || ' ', font: "Courier New", size: 18, color: "2D2D2D" })],
        shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
        indent: { left: 480 },
        spacing: { before: 0, after: 0 },
      }));
    });
    paras.push(new Paragraph({ children: [], spacing: { before: 60, after: 0 } }));
    codeLines = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    // Code fence
    if (line.startsWith('```')) {
      if (!inCode) { inCode = true; continue; }
      else { inCode = false; flushCode(); continue; }
    }
    if (inCode) { codeLines.push(line); continue; }

    // Empty line
    if (!line.trim()) {
      paras.push(new Paragraph({ children: [], spacing: { before: 80, after: 0 } }));
      continue;
    }

    // ## Heading 2
    if (line.startsWith('## ')) {
      const text = line.slice(3).trim();
      paras.push(new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun({ text, bold: true, size: 28, font: "Arial", color: colors.primary })],
        spacing: { before: 280, after: 80 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: colors.accent, space: 4 } },
      }));
      continue;
    }

    // ### Heading 3
    if (line.startsWith('### ')) {
      const text = line.slice(4).trim();
      paras.push(new Paragraph({
        heading: HeadingLevel.HEADING_3,
        children: [new TextRun({ text, bold: true, size: 24, font: "Arial", color: colors.accent })],
        spacing: { before: 200, after: 60 },
      }));
      continue;
    }

    // #### Heading 4
    if (line.startsWith('#### ')) {
      const text = line.slice(5).trim();
      paras.push(new Paragraph({
        children: [new TextRun({ text, bold: true, size: 22, font: "Arial", color: colors.accent })],
        spacing: { before: 140, after: 40 },
      }));
      continue;
    }

    // Bullet list: - or * or •
    if (/^[-*•]\s/.test(line)) {
      const text = line.replace(/^[-*•]\s/, '');
      paras.push(new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: parseInline(text),
        spacing: { before: 40, after: 40 },
      }));
      continue;
    }

    // Numbered list
    if (/^\d+[.)]\s/.test(line)) {
      const text = line.replace(/^\d+[.)]\s/, '');
      paras.push(new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: parseInline(text),
        spacing: { before: 40, after: 40 },
      }));
      continue;
    }

    // Normal paragraph
    paras.push(new Paragraph({
      children: parseInline(line),
      spacing: { before: 60, after: 60 },
    }));
  }

  flushCode();
  return paras;
}

// ── Build document ────────────────────────────────────────────────────────
function buildDoc(title, agentKey, content, date) {
  const colors = AGENT_COLORS[agentKey] || AGENT_COLORS.unknown;
  const agentLabel = AGENT_LABELS[agentKey] || "AI Teaching Team";
  const displayDate = date || new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  const doc = new Document({
    numbering: {
      config: [
        { reference: "bullets",
          levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 260 } } } }]
        },
        { reference: "numbers",
          levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 260 } } } }]
        },
      ]
    },
    styles: {
      default: { document: { run: { font: "Arial", size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 36, bold: true, font: "Arial", color: "FFFFFF" },
          paragraph: { spacing: { before: 0, after: 0 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 28, bold: true, font: "Arial", color: colors.primary },
          paragraph: { spacing: { before: 280, after: 80 }, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 24, bold: true, font: "Arial", color: colors.accent },
          paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 2 } },
      ]
    },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            children: [
              new TextRun({ text: `AI Teaching Team  ·  ${agentLabel}`, size: 18, font: "Arial", color: colors.accent, bold: true }),
              new TextRun({ text: "\t", size: 18 }),
              new TextRun({ text: displayDate, size: 18, font: "Arial", color: "888888" }),
            ],
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: colors.accent, space: 4 } },
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            children: [
              new TextRun({ text: "AI Teaching Agent Team  ·  Powered by qwen2.5:7b via Ollama  ·  Page ", size: 16, font: "Arial", color: "AAAAAA" }),
              new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: "AAAAAA" }),
            ],
            alignment: AlignmentType.CENTER,
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: colors.accent, space: 4 } },
          })]
        })
      },
      children: [
        // ── Banner title ──────────────────────────────────────────────
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun({ text: title, bold: true, size: 36, font: "Arial", color: "FFFFFF" })],
          shading: { fill: colors.primary, type: ShadingType.CLEAR },
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 0 },
          indent: { left: 240, right: 240 },
        }),

        // ── Agent badge ───────────────────────────────────────────────
        new Paragraph({
          children: [new TextRun({ text: `Generated by ${agentLabel}  ·  ${displayDate}`, size: 18, font: "Arial", color: "AAAAAA", italics: true })],
          shading: { fill: colors.light, type: ShadingType.CLEAR },
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 200 },
          indent: { left: 240, right: 240 },
        }),

        // ── Main content ──────────────────────────────────────────────
        ...parseContent(content, colors),

        // ── Footer note ───────────────────────────────────────────────
        new Paragraph({ children: [], spacing: { before: 240, after: 0 } }),
        new Paragraph({
          children: [new TextRun({ text: "AI Teaching Agent Team  ·  qwen2.5:7b via Ollama  ·  Free & Local", size: 16, font: "Arial", color: "AAAAAA", italics: true })],
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: colors.accent, space: 8 } },
        }),
      ]
    }]
  });

  Packer.toBuffer(doc).then(buf => {
    process.stdout.write(buf);
  }).catch(e => {
    process.stderr.write('Packer error: ' + e.message + '\n');
    process.exit(1);
  });
}
