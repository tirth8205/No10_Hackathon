import { openTab, PHONE, DESKTOP } from "./cdp.mjs";
const [, , url, vp = "phone"] = process.argv;
const t = await openTab(); await t.setViewport(vp === "phone" ? PHONE : DESKTOP);
await t.goto(url, 2500);
console.log(await t.eval("location.href"));
console.log(await t.eval("document.body.innerText"));
console.log(await t.eval("[...document.querySelectorAll('a,button,details summary')].map(a => a.tagName+' '+(a.getAttribute('href')||'')+' | '+a.textContent.trim().slice(0,60)).join('\\n')"));
t.close(); process.exit(0);
