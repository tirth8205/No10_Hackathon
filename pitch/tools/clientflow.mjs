// Phone client flow: optional code entry, upload a letter, capture checking + result screens.
// Usage: node pitch/tools/clientflow.mjs <weak|fixed>
import { openTab, PHONE, byText, sleep } from "./cdp.mjs";
const which = process.argv[2];
const pdf = `/Users/zahid/Documents/no10hack/pitch/assets/${which === "fixed" ? "jane-support-letter-fixed.pdf" : "jane-support-letter.pdf"}`;
const P = which === "fixed" ? "p2" : "p1";
const t = await openTab(); await t.setViewport(PHONE);
const exit = "document.querySelector('.govuk-exit-this-page a, .govuk-exit-this-page')";
const common = { exit_this_page_button: exit, header: "document.querySelector('.govuk-header')" };

if (which === "weak") {
  await t.goto("/client", 1500);
  const r = { ...common, heading: "document.querySelector('h1')", code_input: "document.querySelector('#code')", continue_button: byText("button", "Continue"), no_code_details: "document.querySelector('details')" };
  await t.shot("p01-client-enter-code-empty.png", { description: "Phone: 'Enter your code' page, empty. Exit this page button at top.", regions: r });
  await t.eval("document.querySelector('#code').focus(); true");
  await t.send("Input.insertText", { text: "F9JW-SAAY" });
  await t.eval("document.querySelector('#code').blur(); true"); await sleep(300);
  await t.shot("p02-client-enter-code-typed.png", { description: "Phone: 'Enter your code' with F9JW-SAAY typed in.", regions: r });
  await t.eval(`(${byText("button", "Continue")}).click(); true`);
  if (!(await t.waitFor("location.pathname === '/client/F9JWSAAY' && document.querySelector('h1')", 10000))) throw new Error("did not reach upload page");
  await sleep(1500);
} else {
  await t.goto("/client/F9JWSAAY", 2000);
}
const ru = { ...common, firm_caption: "document.querySelector('.govuk-caption-m')", heading: "document.querySelector('h1')", greeting: byText("p", "Hi Jane"), ask_box: "document.querySelector('.app-ask')", take_photos_button: byText("label", "Take photos"), choose_from_phone_button: byText("label", "Choose from your phone"), add_it_here_link: byText("label", "Add it here") };
await t.shot(`${P}-03-client-upload.png`, { description: `Phone: Jane's upload page 'Send your letter' (Hartley & Webb, asked for 'Letter from your support worker')${which === "fixed" ? ", before uploading the corrected letter" : ""}.`, regions: ru });
if (which === "weak") await t.shot(`${P}-03-client-upload-full.png`, { full: true, description: "Phone: upload page, full length (includes 'What happens to my letter?' and link expiry).", regions: ru });

const { root } = await t.send("DOM.getDocument", { depth: -1 });
const { nodeIds } = await t.send("DOM.querySelectorAll", { nodeId: root.nodeId, selector: ".app-phone-upload input[type=file]" });
const inputNode = nodeIds[nodeIds.length - 1]; // "Choose from your phone" (no capture)
const before = Date.now();
await t.send("DOM.setFileInputFiles", { nodeId: inputNode, files: [pdf] });
const sawChecking = await t.waitFor("location.pathname.includes('/checking') && document.querySelector('h1') && document.querySelector('h1').textContent.includes('Checking')", 20000, 80);
const rc = { ...common, heading: "document.querySelector('h1')", spinner_line: "document.querySelector('[role=status]')", file_card: "document.querySelector('.app-file-card')", task_list: "document.querySelector('.govuk-task-list')", checking_tag: byText(".govuk-tag", "Checking") };
let docId = null;
if (sawChecking) {
  await sleep(250);
  docId = await t.eval("new URLSearchParams(location.search).get('doc')");
  await t.shot(`${P}-04-client-checking.png`, { description: "Phone: 'Checking your document' screen with spinner and task list (Reading done / Checking / Waiting).", regions: rc });
} else console.log("checking screen not seen; now at", await t.eval("location.href"));
const done = await t.waitFor("location.pathname.includes('/result/') && document.querySelector('h1, .govuk-panel')", 200000, 1000);
console.log("result after", Math.round((Date.now() - before) / 1000), "s", await t.eval("location.href"));
if (!done) throw new Error("no result within time");
await sleep(1500);
docId = docId || await t.eval("new URLSearchParams(location.search).get('doc')");
console.log("DOCID", docId);
const rr = { ...common, needs_change_tag: byText(".govuk-tag", "Needs a change"), heading: "document.querySelector('h1')", panel: "document.querySelector('.govuk-panel')", missing_requirement_inset: "document.querySelector('.govuk-inset-text')", copy_message_button: byText("button", "Copy a message"), upload_new_letter_button: byText("a.govuk-button", "Upload a new letter"), read_message_details: "document.querySelector('details')", message_text: "document.querySelector('.app-letter')", upload_another_link: byText("a", "Upload another") };
const state = await t.eval("location.pathname.split('/').pop()");
if (which === "weak") {
  await t.shot(`${P}-05-client-result-needs-change.png`, { description: `Phone: result '${state}' - Needs a change: what to add, copy-message button, upload-new-letter button.`, regions: rr });
  await t.shot(`${P}-05-client-result-needs-change-full.png`, { full: true, description: "Phone: needs-a-change result, full page.", regions: rr });
  const h = await t.pageHeight();
  if (h > 844) { await t.scrollTo(h); await t.shot(`${P}-06-client-result-scrolled-bottom.png`, { description: "Phone: needs-a-change result scrolled to bottom (buttons and 'Read the message first').", regions: rr }); }
  // Expand the message
  await t.eval("document.querySelector('details summary').click(); true"); await sleep(600);
  await t.eval("document.querySelector('details').scrollIntoView({block:'start'}); window.scrollBy(0,-80); true"); await sleep(500);
  await t.shot(`${P}-07-client-message-expanded.png`, { description: "Phone: 'Read the message first' expanded, showing the ready-made message to the support worker.", regions: rr });
  await t.shot(`${P}-07-client-message-expanded-full.png`, { full: true, description: "Phone: result with the message to the writer expanded, full page.", regions: rr });
  // Copy
  await t.eval(`(${byText("button", "Copy a message")}).scrollIntoView({block:'center'}); true`); await sleep(400);
  await t.shot(`${P}-08-client-copy-before.png`, { description: "Phone: Copy-a-message button before tapping.", regions: rr });
  await t.eval(`(${byText("button", "Copy a message")}).click(); true`);
  const copied = await t.waitFor(byText("button", "Copied"), 3000, 100);
  console.log("copied", copied, "clipboard:", await t.eval("navigator.clipboard.readText().catch(e => 'ERR '+e)"));
  await t.shot(`${P}-09-client-copy-after.png`, { description: `Phone: after tapping copy - button reads '${copied ? "Copied" : "(did not change)"}'.`, regions: { ...rr, copied_button: byText("button", "Copied") } });
  console.log("MESSAGE", await t.eval("document.querySelector('.app-letter')?.innerText"));
} else {
  // The stub result is wrong; result screens are captured by clientresult.mjs after synth_result.py.
  console.log("STATE", state);
}
console.log("TEXT", await t.eval("document.body.innerText"));
t.close(); process.exit(0);
