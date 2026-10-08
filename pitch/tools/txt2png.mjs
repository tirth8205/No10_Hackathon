// Render a plain-text file to a clean PNG (as a text editor would show it) via headless Chrome.
// Usage: node pitch/tools/txt2png.mjs <in.txt> <out.png> <title>
import { readFileSync, writeFileSync } from "node:fs";
import { openTab, sleep, addManifest } from "./cdp.mjs";
const [, , inp, out, title] = process.argv;
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const html = `<!doctype html><meta charset=utf-8><style>body{margin:0;background:#fff;font:15px/1.55 Menlo,Consolas,monospace;color:#111}
.bar{background:#eceef1;border-bottom:1px solid #d0d4da;padding:10px 20px;font:600 13px -apple-system,Helvetica,Arial,sans-serif;color:#333}
pre{margin:0;padding:24px 28px;white-space:pre-wrap;word-break:break-word}</style><div class=bar>${esc(title)}</div><pre>${esc(readFileSync(inp, "utf8"))}</pre>`;
const t = await openTab();
await t.setViewport({ width: 900, height: 600, deviceScaleFactor: 2, mobile: false });
const { frameTree } = await t.send("Page.getFrameTree");
await t.send("Page.setDocumentContent", { frameId: frameTree.frame.id, html });
await sleep(400);
const h = await t.eval("document.documentElement.scrollHeight");
await t.setViewport({ width: 900, height: h, deviceScaleFactor: 2, mobile: false }); await sleep(300);
const s = await t.send("Page.captureScreenshot", { format: "png" });
writeFileSync(out, Buffer.from(s.data, "base64"));
console.log(out, h);
t.close(); process.exit(0);
