// Minimal raw-CDP helper for capturing app screenshots. Used by pitch/tools/shoot.mjs.
import { writeFileSync, readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

export const ROOT = resolve(new URL("../..", import.meta.url).pathname);
export const SHOTS = `${ROOT}/pitch/shots`;
export const APP = "http://localhost:5173";
export const DESKTOP = { width: 1440, height: 900, deviceScaleFactor: 2, mobile: false };
export const PHONE = { width: 390, height: 844, deviceScaleFactor: 3, mobile: true };
const MANIFEST = `${SHOTS}/manifest.json`;
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function openTab() {
  const target = await (await fetch(`http://127.0.0.1:9333/json/new?about:blank`, { method: "PUT" })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0; const pending = new Map();
  ws.onmessage = (m) => { const msg = JSON.parse(m.data); if (pending.has(msg.id)) { const p = pending.get(msg.id); pending.delete(msg.id); msg.error ? p.rej(new Error(JSON.stringify(msg.error))) : p.res(msg.result); } };
  await new Promise((r) => (ws.onopen = r));
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
  await send("Page.enable"); await send("Runtime.enable"); await send("DOM.enable");
  await send("Emulation.setFocusEmulationEnabled", { enabled: true });
  await send("Browser.grantPermissions", { origin: APP, permissions: ["clipboardReadWrite", "clipboardSanitizedWrite"] }).catch(() => {});
  const t = {
    send, ws, viewport: null,
    async setViewport(v) {
      t.viewport = v;
      await send("Emulation.setDeviceMetricsOverride", { width: v.width, height: v.height, deviceScaleFactor: v.deviceScaleFactor, mobile: v.mobile });
      await send("Emulation.setScrollbarsHidden", { hidden: true }).catch(() => {});
      await send("Emulation.setTouchEmulationEnabled", { enabled: !!v.mobile, maxTouchPoints: v.mobile ? 5 : 1 });
      if (v.mobile) await send("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" });
    },
    async eval(expr) {
      const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true, userGesture: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 500));
      return r.result.value;
    },
    async goto(url, settle = 1200) {
      await send("Page.navigate", { url: url.startsWith("http") ? url : APP + url });
      await t.waitFor("document.readyState === 'complete'", 15000);
      await sleep(settle);
    },
    async waitFor(expr, timeout = 10000, every = 250) {
      const end = Date.now() + timeout;
      while (Date.now() < end) { try { if (await t.eval(`!!(${expr})`)) return true; } catch {} await sleep(every); }
      return false;
    },
    async scrollTo(y) { await t.eval(`window.scrollTo(0, ${y}); true`); await sleep(400); },
    async pageHeight() { return t.eval("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)"); },
    // Boxes in CSS px relative to the screenshot (viewport shot: relative to current viewport; full: relative to document).
    async boxes(map, full = false) {
      const out = {};
      for (const [name, js] of Object.entries(map)) {
        const b = await t.eval(`(() => { const el = (${js}); if (!el) return null; const r = el.getBoundingClientRect(); const sy = ${full ? "window.scrollY" : 0}, sx = ${full ? "window.scrollX" : 0}; return {x: Math.round(r.left+sx), y: Math.round(r.top+sy), w: Math.round(r.width), h: Math.round(r.height)}; })()`).catch(() => null);
        if (b && b.w > 0 && b.h > 0) { if (!full) { const vh = t.viewport.height; if (b.y + b.h <= 0 || b.y >= vh) continue; if (b.y < 0 || b.y + b.h > vh) b.partlyOffscreen = true; } out[name] = b; }
      }
      return out;
    },
    async shot(file, { full = false, description = "", regions = {}, notes } = {}) {
      const v = t.viewport;
      let params = { format: "png" }, height = v.height;
      let savedY = 0;
      if (full) {
        t._full = true;
        savedY = await t.eval("window.scrollY");
        await t.scrollTo(0);
        height = await t.pageHeight();
        await send("Emulation.setDeviceMetricsOverride", { width: v.width, height, deviceScaleFactor: v.deviceScaleFactor, mobile: v.mobile });
        await sleep(700);
      }
      const boxes = await t.boxes(regions, full);
      const url = await t.eval("location.pathname + location.search");
      const scrollY = full ? 0 : await t.eval("Math.round(window.scrollY)");
      const text = await t.eval("document.body.innerText");
      const r = await send("Page.captureScreenshot", params);
      writeFileSync(`${SHOTS}/${file}`, Buffer.from(r.data, "base64"));
      if (full) { await t.setViewport(v); await sleep(300); await t.scrollTo(savedY); }
      const flags = [];
      if (/offline stub/i.test(text)) flags.push("contains 'offline stub' text: crop it");
      if (/paid[^.\n]{0,40}sooner/i.test(text)) flags.push("contains 'get paid ... sooner' wording (breaks the rule): crop or avoid that banner");
      if (/\bestimat/i.test(text)) flags.push("mentions an estimate: check it is labelled");
      const entry = { file, url, viewport: { ...v, height: full ? height : v.height, fullPage: full }, scrollY, description,
        units: `CSS px; multiply by ${v.deviceScaleFactor} for image pixels`, regions: boxes, ...(notes ? { notes } : {}), ...(flags.length ? { flags } : {}) };
      addManifest(entry);
      console.log("shot", file, JSON.stringify(boxes));
      return entry;
    },
    close() { ws.close(); },
  };
  return t;
}

export function addManifest(entry) {
  const list = existsSync(MANIFEST) ? JSON.parse(readFileSync(MANIFEST, "utf8")) : [];
  const i = list.findIndex((e) => e.file === entry.file);
  if (i >= 0) list[i] = entry; else list.push(entry);
  writeFileSync(MANIFEST, JSON.stringify(list, null, 2));
}

// Find an element by visible text (returns JS expression).
export const byText = (sel, text) => `[...document.querySelectorAll(${JSON.stringify(sel)})].find(e => e.textContent.trim().includes(${JSON.stringify(text)}))`;
