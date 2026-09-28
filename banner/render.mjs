// Render a banner JSON spec to a print PDF (real size, vector text) and a PNG preview.
//
//   node banner/render.mjs banner/examples/sample.json
//
// Output goes to out/<json-name>.pdf and out/<json-name>.png
import { chromium } from "playwright";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const specPath = process.argv[2];
if (!specPath) {
  console.error("usage: node banner/render.mjs <spec.json>");
  process.exit(1);
}

const spec = JSON.parse(await readFile(specPath, "utf8"));
const { widthMm = 5000, heightMm = 900, previewWidthPx = 3000 } = spec.size ?? {};
const name = path.basename(specPath, ".json");
const outDir = path.resolve(here, "..", "out");
await mkdir(outDir, { recursive: true });

const executablePath = process.env.PLAYWRIGHT_BROWSERS_PATH === "/opt/pw-browsers" ? "/opt/pw-browsers/chromium" : undefined;
const browser = await chromium.launch(executablePath ? { executablePath } : {});

async function renderPage(W, H, viewport) {
  const page = await browser.newPage({ viewport });
  await page.goto(pathToFileURL(path.join(here, "template.html")).href);
  await page.evaluate(({ spec, W, H }) => {
    const root = document.documentElement.style;
    root.setProperty("--W", W);
    root.setProperty("--H", H);
    document.body.dataset.theme = spec.theme ?? "light";
    document.body.dataset.align = spec.align ?? "left";
    // custom colors override the theme (set on body, where the theme vars live)
    for (const [k, v] of Object.entries(spec.colors ?? {})) document.body.style.setProperty(`--${k}`, v);

    // *text* -> accent color, \n -> line break
    const fmt = (s = "") =>
      s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c])
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/\n/g, "<br>");
    for (const id of ["eyebrow", "title", "subtitle", "info", "org"]) {
      document.getElementById(id).innerHTML = fmt(spec[id]);
    }
    if (!spec.info && !spec.org) document.getElementById("footer").style.display = "none";
  }, { spec, W, H });
  await page.evaluate(() => document.fonts.ready);

  // Shrink any line that would overflow the safe area.
  await page.evaluate(() => {
    const box = document.querySelector(".banner");
    const maxW = box.clientWidth - parseFloat(getComputedStyle(box).paddingLeft) * 2;
    for (const el of document.querySelectorAll(".title, .subtitle")) {
      let size = parseFloat(getComputedStyle(el).fontSize);
      while (el.scrollWidth > maxW && size > 4) {
        size *= 0.97;
        el.style.fontSize = `${size}px`;
      }
    }
  });
  return page;
}

// Print PDF at real size. Text stays vector, so it is sharp at any scale.
const pdfPage = await renderPage(`${widthMm}mm`, `${heightMm}mm`, { width: 1600, height: 900 });
const pdfPath = path.join(outDir, `${name}.pdf`);
await pdfPage.pdf({ path: pdfPath, width: `${widthMm}mm`, height: `${heightMm}mm`, printBackground: true, pageRanges: "1" });

// PNG preview at the same aspect ratio.
const pw = previewWidthPx;
const ph = Math.round((pw * heightMm) / widthMm);
const pngPage = await renderPage(`${pw}px`, `${ph}px`, { width: pw, height: ph });
const pngPath = path.join(outDir, `${name}.png`);
await pngPage.screenshot({ path: pngPath, clip: { x: 0, y: 0, width: pw, height: ph } });

await browser.close();
console.log(`PDF : ${pdfPath}\nPNG : ${pngPath}`);
