// Render an HTML scene to a silent MP4, frame by frame.
// Usage: node pitch/render.mjs pitch/clip1/scene.html pitch/clip1/clip1.mp4 15
// Needs a Chromium with --remote-debugging-port=9333 running, and ffmpeg.
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";

const [, , scenePath, outPath, secondsArg = "15", fpsArg = "30"] = process.argv;
const seconds = Number(secondsArg), fps = Number(fpsArg);
const frames = Math.round(seconds * fps);
const framesDir = resolve(dirname(outPath), "frames");
rmSync(framesDir, { recursive: true, force: true });
mkdirSync(framesDir, { recursive: true });

const target = await (await fetch(`http://127.0.0.1:9333/json/new?${encodeURIComponent("file://" + resolve(scenePath))}`, { method: "PUT" })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
ws.onmessage = (m) => { const msg = JSON.parse(m.data); if (pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); } };
await new Promise((r) => (ws.onopen = r));
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
await send("Page.reload", { ignoreCache: true });
await new Promise((r) => setTimeout(r, 1500));
// Freeze every animation, then step them to each frame's time: exact timing, no dropped frames.
await send("Runtime.evaluate", { expression: "document.getAnimations().forEach(a => a.pause()); true" });
for (let f = 0; f < frames; f++) {
  const t = (f * 1000) / fps;
  await send("Runtime.evaluate", { expression: `document.getAnimations().forEach(a => { a.currentTime = ${t}; }); true` });
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${framesDir}/f${String(f).padStart(4, "0")}.png`, Buffer.from(shot.data, "base64"));
}
ws.close();
// Close the tab: leaving one open per render slowly grinds a shared Chrome to a halt.
await fetch(`http://127.0.0.1:9333/json/close/${target.id}`).catch(() => {});
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(fps), "-i", `${framesDir}/f%04d.png`,
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", "-an", outPath]);
rmSync(framesDir, { recursive: true, force: true });
console.log(`wrote ${outPath}: ${frames} frames, ${seconds}s at ${fps}fps, no audio`);
process.exit(0);
