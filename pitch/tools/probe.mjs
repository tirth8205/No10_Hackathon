// Usage: node pitch/tools/probe.mjs <path> [phone]  -> prints page text and height
import { openTab, DESKTOP, PHONE } from "./cdp.mjs";
const t = await openTab(); await t.setViewport(process.argv[3] === "phone" ? PHONE : DESKTOP);
await t.goto(process.argv[2], 2500);
console.log(await t.eval("document.body.innerText"));
console.log("HEIGHT", await t.pageHeight());
t.close(); process.exit(0);
