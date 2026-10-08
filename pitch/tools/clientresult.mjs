// Phone: capture the client result screen for an already-checked (synthesised) document.
// Usage: node pitch/tools/clientresult.mjs <docId> <weak|fixed>
import { openTab, PHONE, byText, sleep } from "./cdp.mjs";
const [, , docId, which] = process.argv;
const P = which === "fixed" ? "p2" : "p1";
const t = await openTab(); await t.setViewport(PHONE);
const state = which === "fixed" ? "ready" : "change";
await t.goto(`/client/F9JWSAAY/result/${state}?doc=${docId}`, 3000);
const exit = "document.querySelector('.govuk-exit-this-page a, .govuk-exit-this-page')";
const rr = { exit_this_page_button: exit, header: "document.querySelector('.govuk-header')", needs_change_tag: byText(".govuk-tag", "Needs a change"), heading: "document.querySelector('h1')", panel: "document.querySelector('.govuk-panel')", missing_requirement_inset: "document.querySelector('.govuk-inset-text')", copy_message_button: byText("button", "Copy a message"), upload_new_letter_button: byText("a.govuk-button", "Upload a new letter"), read_message_details: "document.querySelector('details')", message_text: "document.querySelector('.app-letter')", upload_another_link: byText("a", "Upload another") };
const text = await t.eval("document.body.innerText");
console.log("TEXT", text);
if (/offline stub/i.test(text)) throw new Error("stub text on page");
if (which !== "fixed") {
  await t.shot(`${P}-05-client-result-needs-change.png`, { description: "Phone: weak letter result - 'Needs a change': what to add (specific matters relied on), copy-message button, upload-new-letter button.", regions: rr });
  await t.shot(`${P}-05-client-result-needs-change-full.png`, { full: true, description: "Phone: needs-a-change result, full page.", regions: rr });
  const h = await t.pageHeight();
  if (h > 844) { await t.scrollTo(h); await t.shot(`${P}-06-client-result-scrolled-bottom.png`, { description: "Phone: needs-a-change result scrolled to bottom.", regions: rr }); }
  await t.scrollTo(0);
  await t.eval("document.querySelector('details summary').click(); true"); await sleep(600);
  await t.eval("document.querySelector('details').scrollIntoView({block:'start'}); window.scrollBy(0,-80); true"); await sleep(500);
  await t.shot(`${P}-07-client-message-expanded.png`, { description: "Phone: 'Read the message first' expanded, showing the ready-made message to the support worker.", regions: rr });
  await t.shot(`${P}-07-client-message-expanded-full.png`, { full: true, description: "Phone: result with the message to the writer expanded, full page.", regions: rr });
  await t.eval(`(${byText("button", "Copy a message")}).scrollIntoView({block:'center'}); true`); await sleep(400);
  await t.shot(`${P}-08-client-copy-before.png`, { description: "Phone: Copy-a-message button before tapping.", regions: rr });
  await t.eval(`(${byText("button", "Copy a message")}).click(); true`);
  const copied = await t.waitFor(byText("button", "Copied"), 3000, 100);
  console.log("copied", copied);
  await t.shot(`${P}-09-client-copy-after.png`, { description: `Phone: after tapping copy - button reads '${copied ? "Copied" : "(did not change)"}'.`, regions: { ...rr, copied_button: byText("button", "Copied") } });
  console.log("MESSAGE", await t.eval("document.querySelector('.app-letter')?.innerText"));
} else {
  await t.shot(`${P}-05-client-result-ready.png`, { description: "Phone: corrected letter result - ready.", regions: rr });
  await t.shot(`${P}-05-client-result-ready-full.png`, { full: true, description: "Phone: corrected-letter result, full page.", regions: rr });
}
t.close(); process.exit(0);
