// build_docx.js  —  renders a report model (JSON) into a .docx file with docx-js
// usage: node build_docx.js model.json out.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, PageBreak, Header, Footer, PageNumber,
  LevelFormat, TabStopType, TabStopPosition, Tab, PositionalTab, PositionalTabAlignment,
  PositionalTabRelativeTo, PositionalTabLeader, VerticalAlign, TableLayoutType,
} = require("docx");

const [, , modelPath, outPath] = process.argv;
const model = JSON.parse(fs.readFileSync(modelPath, "utf8"));

const TEAL = "0F766E", DARK = "0B3B37", GREY = "5B6B66", LINE = "B7C6C2";
const PAGE_W = 11906, MARGIN = 1247;                 // A4, ~2.2 cm margins
const CONTENT_W = PAGE_W - 2 * MARGIN;               // DXA
const dxa = (inches) => Math.round(inches * 1440);

// ---- inline markup: **bold**, `code`, _italic_
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const s = m[0];
    if (s.startsWith("**")) out.push(new TextRun({ text: s.slice(2, -2), bold: true, ...base }));
    else if (s.startsWith("`")) out.push(new TextRun({ text: s.slice(1, -1), font: "Consolas", size: 19, color: "7C2D12", ...base }));
    else out.push(new TextRun({ text: s.slice(1, -1), italics: true, ...base }));
    last = m.index + s.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const cellBorders = { top: border, bottom: border, left: border, right: border };

function table(b) {
  const total = b.widths.reduce((a, c) => a + c, 0);
  const cols = b.widths.map((w) => Math.floor((w / total) * CONTENT_W));
  cols[cols.length - 1] += CONTENT_W - cols.reduce((a, c) => a + c, 0);
  const mkCell = (txt, i, header, shade) => new TableCell({
    width: { size: cols[i], type: WidthType.DXA },
    borders: cellBorders,
    shading: header ? { fill: TEAL, type: ShadingType.CLEAR, color: "auto" }
                    : shade ? { fill: "F1F6F5", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    verticalAlign: VerticalAlign.CENTER,
    children: String(txt).split("\n").map((line) => new Paragraph({
      spacing: { before: 0, after: 0, line: 252 },
      children: runs(line, header ? { bold: true, color: "FFFFFF", size: 19 } : { size: 19 }),
    })),
  });
  const rows = [new TableRow({ tableHeader: true, children: b.header.map((h, i) => mkCell(h, i, true)) })];
  b.rows.forEach((r, ri) => rows.push(new TableRow({ children: r.map((c, i) => mkCell(c, i, false, ri % 2 === 1)) })));
  return new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: cols, rows, layout: TableLayoutType.FIXED });
}

function caption(text) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 220 },
    children: [new TextRun({ text, italics: true, size: 19, color: GREY })] });
}

function image(b) {
  const buf = fs.readFileSync(b.path);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);         // PNG IHDR
  let wIn = b.w || 6.3;
  let hIn = (wIn * h) / w;
  const maxH = b.maxh || 8.6;
  if (hIn > maxH) { wIn = (wIn * maxH) / hIn; hIn = maxH; }
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 0 }, keepNext: true,
    children: [new ImageRun({ type: "png", data: buf,
      transformation: { width: Math.round(wIn * 96), height: Math.round(hIn * 96) },
      altText: { title: b.caption || "figure", description: b.caption || "figure", name: path.basename(b.path) } })] });
}

function codeBlock(b) {
  const out = [];
  if (b.title) out.push(new Paragraph({ spacing: { before: 160, after: 60 }, keepNext: true,
    children: [new TextRun({ text: b.title, bold: true, size: 20, color: DARK })] }));
  b.lines.forEach((line, i) => out.push(new Paragraph({
    spacing: { before: 0, after: 0, line: 228 },
    shading: { fill: "F4F6F5", type: ShadingType.CLEAR, color: "auto" },
    border: i === 0 ? { top: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 2 } }
          : i === b.lines.length - 1 ? { bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 2 } } : undefined,
    children: [new TextRun({ text: line.length ? line.replace(/\t/g, "    ") : " ", font: "Consolas", size: 15 })],
  })));
  out.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
  return out;
}

function note(b) {
  const colors = { warn: ["FEF3C7", "B45309"], info: ["E6F4F1", TEAL], danger: ["FEE2E2", "B91C1C"] };
  const [fill, col] = colors[b.kind || "info"];
  return new Paragraph({
    spacing: { before: 120, after: 160 },
    shading: { fill, type: ShadingType.CLEAR, color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 24, color: col, space: 8 } },
    indent: { left: 160, right: 160 },
    children: runs(b.text, { size: 21 }),
  });
}

let numberInstance = 0;
function blocks(list) {
  const out = [];
  for (const b of list) {
    switch (b.t) {
      case "h1": out.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: !b.nobreak, children: [new TextRun(b.text)] })); break;
      case "h2": out.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(b.text)] })); break;
      case "h3": out.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(b.text)] })); break;
      case "p": out.push(new Paragraph({ spacing: { after: 140, line: 300 }, alignment: AlignmentType.JUSTIFIED, children: runs(b.text) })); break;
      case "bullets": b.items.forEach((it) => out.push(new Paragraph({ numbering: { reference: "bul", level: 0 },
        spacing: { after: 60, line: 288 }, children: runs(it) }))); out.push(new Paragraph({ spacing: { after: 60 }, children: [] })); break;
      case "numbers": numberInstance++; b.items.forEach((it) => out.push(new Paragraph({
        numbering: { reference: "num", level: 0, instance: numberInstance }, spacing: { after: 70, line: 288 }, children: runs(it) })));
        out.push(new Paragraph({ spacing: { after: 60 }, children: [] })); break;
      case "table": out.push(table(b)); if (b.caption) out.push(caption(b.caption)); else out.push(new Paragraph({ children: [] })); break;
      case "img": out.push(image(b)); if (b.caption) out.push(caption(b.caption)); break;
      case "code": out.push(...codeBlock(b)); break;
      case "note": out.push(note(b)); break;
      case "pb": out.push(new Paragraph({ children: [new PageBreak()] })); break;
      case "toc":
        out.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun("Contents")] }));
        b.entries.forEach((e) => out.push(new Paragraph({
          spacing: { before: e.level === 1 ? 110 : 20, after: 20 },
          indent: { left: e.level === 1 ? 0 : 400 },
          tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W, leader: "dot" }],
          children: [new TextRun({ text: e.text, bold: e.level === 1, size: e.level === 1 ? 22 : 20 }),
                     new TextRun({ children: [new Tab(), String(e.page || "")],
                       bold: e.level === 1, size: e.level === 1 ? 22 : 20 })],
        })));
        break;
      case "title": out.push(...titlePage(b)); break;
      default: throw new Error("unknown block " + b.t);
    }
  }
  return out;
}

function titlePage(b) {
  const P = (text, opt = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: opt.after ?? 120, before: opt.before ?? 0 },
    children: [new TextRun({ text, ...opt.run })] });
  const out = [
    P("A PROJECT REPORT ON", { before: 600, after: 200, run: { size: 24, color: GREY, bold: true, characterSpacing: 40 } }),
    P(b.title, { after: 160, run: { size: 44, bold: true, color: DARK } }),
    P(b.subtitle, { after: 400, run: { size: 24, color: TEAL } }),
  ];
  if (b.img) out.push(image({ path: b.img, w: 4.6, maxh: 2.9 }));
  out.push(P("", { after: 300 }));
  for (const [k, v] of b.fields) {
    out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 90 },
      children: [new TextRun({ text: k + ": ", bold: true, size: 22, color: DARK }), new TextRun({ text: v, size: 22 })] }));
  }
  out.push(P(b.date, { before: 500, run: { size: 22, color: GREY } }));
  return out;
}

const doc = new Document({
  creator: model.meta.author || "ESP32 IoT Projects",
  title: model.meta.title,
  description: model.meta.description,
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 34, bold: true, font: "Calibri", color: DARK },
        paragraph: { spacing: { before: 120, after: 220 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: TEAL, space: 6 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Calibri", color: TEAL },
        paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: "Calibri", color: DARK },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 340 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 1247, bottom: 1134, left: MARGIN, right: MARGIN, header: 560, footer: 520 } },
                  titlePage: true },
    headers: {
      first: new Header({ children: [new Paragraph({ children: [] })] }),
      default: new Header({ children: [new Paragraph({
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 4 } },
        tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }],
        children: [new TextRun({ text: model.meta.header, size: 17, color: GREY }),
                   new TextRun({ children: [new Tab(), model.meta.headerRight], size: 17, color: GREY })] })] }),
    },
    footers: {
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: ["Page ", PageNumber.CURRENT], size: 18, color: GREY })] })] }),
    },
    children: blocks(model.blocks),
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("wrote", outPath); });
