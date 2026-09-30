// HTML → 실제 크기 PDF (글자는 벡터로 유지)
//   node scripts/render_pdf.mjs <in.html> <out.pdf> <width_mm> <height_mm>
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch {
  ({ chromium } = require("/opt/node22/lib/node_modules/playwright"));
}

const [inHtml, outPdf, w, h] = process.argv.slice(2);
const launch = process.env.PLAYWRIGHT_BROWSERS_PATH === "/opt/pw-browsers" ? { executablePath: "/opt/pw-browsers/chromium" } : {};
const browser = await chromium.launch(launch);
const page = await browser.newPage();
await page.goto(pathToFileURL(path.resolve(inHtml)).href, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.pdf({ path: outPdf, width: `${w}mm`, height: `${h}mm`, printBackground: true, pageRanges: "1" });
await browser.close();
console.log("saved", outPdf);
