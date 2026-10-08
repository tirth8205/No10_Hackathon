// Phone: the 'Checking your document' screen. The live screen shows only for a moment (the check
// returns within the upload request), so this renders the real page while the client-document API
// response is rewritten to "no result yet" via CDP Fetch interception.
// Usage: node pitch/tools/checking.mjs <docId> <prefix>
import { openTab, PHONE, byText, sleep } from "./cdp.mjs";
const [, , docId, P] = process.argv;
const t = await openTab(); await t.setViewport(PHONE);
await t.send("Fetch.enable", { patterns: [{ urlPattern: `*/web/client/*/documents/${docId}*`, requestStage: "Response" }] });
t.ws.addEventListener("message", async (m) => {
  const msg = JSON.parse(m.data);
  if (msg.method !== "Fetch.requestPaused") return;
  const { requestId } = msg.params;
  const body = await t.send("Fetch.getResponseBody", { requestId });
  let json; try { json = JSON.parse(body.base64Encoded ? Buffer.from(body.body, "base64").toString() : body.body); } catch { return t.send("Fetch.continueRequest", { requestId }); }
  json.document.result = null; json.state = null;
  await t.send("Fetch.fulfillRequest", { requestId, responseCode: 200, responseHeaders: [{ name: "content-type", value: "application/json" }], body: Buffer.from(JSON.stringify(json)).toString("base64") });
});
await t.goto(`/client/F9JWSAAY/checking?doc=${docId}`, 2500);
await t.waitFor("document.querySelector('h1') && document.querySelector('h1').textContent.includes('Checking')", 10000);
await sleep(800);
const rc = { exit_this_page_button: "document.querySelector('.govuk-exit-this-page a, .govuk-exit-this-page')", heading: "document.querySelector('h1')", spinner_line: "document.querySelector('[role=status]')", file_card: "document.querySelector('.app-file-card')", task_list: "document.querySelector('.govuk-task-list')", checking_tag: byText(".govuk-tag", "Checking") };
await t.shot(`${P}-04-client-checking.png`, { description: "Phone: 'Checking your document' screen (spinner, task list).", regions: rc,
  notes: "Rendered by the real page with the document API response held at 'no result yet' (CDP interception): live, this screen shows for under a second because the check finished inside the upload request." });
console.log(await t.eval("document.body.innerText"));
t.close(); process.exit(0);
