// Desktop: choose the corrected letter on the evidence page, open submit, download (submits), capture confirmation.
import { mkdirSync } from "node:fs";
import { openTab, DESKTOP, byText, sleep, ROOT } from "./cdp.mjs";
const C = "30a14cc479f5cd2b", FIXED = process.argv[2], WEAK = process.argv[3];
const t = await openTab(); await t.setViewport(DESKTOP);
const dl = `${ROOT}/pitch/shots/pack-download`; mkdirSync(dl, { recursive: true });
await t.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: dl }).catch(e => console.log("dl", e.message));
await t.goto(`/provider/cases/${C}`, 2500);
const boxes = await t.eval(`[...document.querySelectorAll('input[type=checkbox]')].map(i => ({id: i.id, value: i.value, checked: i.checked, label: i.closest('.govuk-checkboxes__item')?.innerText.slice(0,120)}))`);
console.log(JSON.stringify(boxes, null, 1));
// tick the corrected letter only
await t.eval(`(() => { for (const i of document.querySelectorAll('input[type=checkbox]')) { const want = i.value === ${JSON.stringify(FIXED)} || i.id.includes(${JSON.stringify(FIXED)}); if (i.checked !== want) i.click(); } return true; })()`);
await sleep(800);
console.log(await t.eval(`[...document.querySelectorAll('input[type=checkbox]')].map(i => i.value + ':' + i.checked).join(' ')`));
const re = { fixed_checkbox: `[...document.querySelectorAll('input[type=checkbox]')].find(i => i.id === "select-" + ${JSON.stringify(FIXED)})?.closest('.govuk-checkboxes__item')`,
  weak_checkbox: `[...document.querySelectorAll('input[type=checkbox]')].find(i => i.id === "select-" + ${JSON.stringify(WEAK)})?.closest('.govuk-checkboxes__item')`,
  continue_button: byText("a.govuk-button", "Continue to submit"), choose_heading: byText("h2", "Choose what to submit") };
const y = await t.eval(`Math.max(0, Math.round((${re.choose_heading}).getBoundingClientRect().top + scrollY - 40))`);
await t.scrollTo(y);
await t.shot("d3-01-evidence-choose-corrected.png", { description: "Evidence tab: corrected letter ticked to submit, weak letter unticked, Continue to submit.", regions: re });
if (process.argv[4] === "choose-only") { t.close(); process.exit(0); }
await t.eval(`(${re.continue_button}).click(); true`);
await t.waitFor("location.pathname.endsWith('/submit') && document.querySelector('h1')", 10000); await sleep(2000);
console.log("submit url", await t.eval("location.href"));
const rs = { heading: "document.querySelector('h1')", ready_panel: "document.querySelector('.govuk-panel, .govuk-notification-banner')", evidence_summary: byText("h2", "Evidence you"),
  download_button: byText("button", "Download for Civil Apply"), getting_paid_aside: byText(".app-aside, aside, div", "Getting paid"), sooner_sentence: byText("p", "sooner"), estimate_label: byText("p", "Estimate based"), pilot_aside: byText("div", "Proposed pilot") };
await t.shot("d3-02-submit.png", { description: "Submit page: 'Ready to submit', the corrected letter, 'Download for Civil Apply' button.", regions: rs });
await t.shot("d3-02-submit-full.png", { full: true, description: "Submit page, full.", regions: rs });
await t.eval(`(${rs.download_button}).scrollIntoView({block:'center'}); true`); await sleep(400);
await t.shot("d3-03-submit-download-button.png", { description: "Submit page with the Download for Civil Apply button centred.", regions: rs });
await t.eval(`(${rs.download_button}).click(); true`);
await t.waitFor("!document.body.innerText.includes('Download for Civil Apply') || document.querySelector('.govuk-panel--confirmation, .govuk-notification-banner--success')", 20000);
await sleep(2500);
const text = await t.eval("document.body.innerText"); console.log("AFTER", text.slice(0, 1500));
const rc = { heading: "document.querySelector('h1')", confirmation_panel: "document.querySelector('.govuk-panel')", success_banner: "document.querySelector('.govuk-notification-banner--success')", download_again: byText("a, button", "Download") };
await t.shot("d3-04-submitted-confirmation.png", { description: "After Download for Civil Apply: confirmation that the evidence pack was created/submitted.", regions: rc });
await t.shot("d3-04-submitted-confirmation-full.png", { full: true, description: "Submitted confirmation, full page.", regions: rc });
t.close(); process.exit(0);
