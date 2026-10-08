// Desktop provider screens for one checked document.
// Usage: node pitch/tools/providerdoc.mjs <docId> <prefix e.g. d1|d2> <weak|fixed>
import { writeFileSync } from "node:fs";
import { openTab, DESKTOP, byText, sleep, SHOTS, addManifest } from "./cdp.mjs";
const [, , docId, P, which] = process.argv;
const C = "30a14cc479f5cd2b";
const label = which === "fixed" ? "corrected letter (all 8 included)" : "weak letter (7 of 8, missing specific matters relied on)";
const t = await openTab(); await t.setViewport(DESKTOP);
const banner = byText(".govuk-notification-banner, .app-payment-banner, section, div", "Getting paid");
async function crop(file, sel, pad, description) {
  const b = await t.eval(`(() => { const el = (${sel}); if (!el) return null; el.scrollIntoView({block:'center'}); return true; })()`);
  if (!b) { console.log("crop target missing", file); return; }
  await sleep(500);
  const r = await t.eval(`(() => { const r = (${sel}).getBoundingClientRect(); return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height}; })()`);
  const clip = { x: Math.max(0, r.x - pad), y: Math.max(0, r.y - pad), width: r.w + 2 * pad, height: r.h + 2 * pad, scale: 1 };
  const s = await t.send("Page.captureScreenshot", { format: "png", clip, captureBeyondViewport: true });
  writeFileSync(`${SHOTS}/${file}`, Buffer.from(s.data, "base64"));
  addManifest({ file, url: await t.eval("location.pathname"), viewport: { ...DESKTOP, crop: true }, description, units: "crop image at 2x; clip (CSS px, document coords) given", clip, regions: {} });
  console.log("crop", file, JSON.stringify(clip));
}

// Evidence page
await t.goto(`/provider/cases/${C}`, 2500);
const re = { case_heading: "document.querySelector('h1')", status_tag: "document.querySelector('h1 .govuk-tag') || document.querySelector('.app-heading-with-tag .govuk-tag')", getting_paid_banner: byText(".govuk-notification-banner", "Getting paid"),
  choose_heading: byText("h2", "Choose what to submit"), document_rows: "document.querySelector('.govuk-checkboxes') || document.querySelector('.app-doc-list')",
  weak_letter_row: byText(".govuk-checkboxes__item, li, tr", "Victim testimony"), see_the_check_link: byText("a", "See the check"), continue_button: byText("a.govuk-button", "Continue to submit") };
await t.shot(`${P}-01-case-evidence.png`, { description: `Jane's case Evidence tab with the ${label}.`, regions: re });
await t.shot(`${P}-01-case-evidence-full.png`, { full: true, description: `Jane's case Evidence tab, full page, with the ${label}.`, regions: re });
const yChoose = await t.eval(`Math.max(0, Math.round((${re.choose_heading}).getBoundingClientRect().top + scrollY - 40))`);
await t.scrollTo(yChoose);
await t.shot(`${P}-01-case-evidence-documents.png`, { description: `Evidence tab scrolled to 'Choose what to submit' document list (${label}).`, regions: re });

// Document check page
await t.goto(`/provider/cases/${C}/documents/${docId}`, 2500);
const rd = { heading: "document.querySelector('h1')", verdict_tag: "document.querySelector('.app-heading-with-tag .govuk-tag')", getting_paid_banner: byText(".govuk-notification-banner", "Getting paid"),
  summary_heading: byText("h2", which === "fixed" ? "" : "One change before you submit"), missing_requirement_heading: byText("h3, h2", "Specific matters relied on"),
  what_letter_says_quote: byText("p, blockquote", "Victim testimony and referral"), what_to_ask_box: byText("div, section", "What to ask Riverside Outreach for"),
  copy_request_button: byText("button", "Copy request"), download_request_button: byText("button", "Download request"), preview_request_details: byText("details", "Preview the request"),
  request_letter_text: "document.querySelector('.app-letter')", drop_corrected_zone: byText("div, section", "Drop the corrected letter here"), all_requirements_details: byText("details", "All 8 requirements"),
  version_changes: byText("div, section, ul", "Previous letter:"), submit_warning: "document.querySelector('.govuk-warning-text')" };
await t.shot(`${P}-02-document-check.png`, { description: `Document check page, top (${label}).`, regions: rd });
await t.shot(`${P}-02-document-check-full.png`, { full: true, description: `Document check page, full (${label}), details closed.`, regions: rd });
const hasPreview = await t.eval(`!!(${rd.preview_request_details})`);
if (hasPreview) {
  await t.eval(`(${rd.preview_request_details}).open = true; true`); await sleep(500);
  const y = await t.eval(`Math.max(0, Math.round((${rd.missing_requirement_heading} || ${rd.what_to_ask_box}).getBoundingClientRect().top + scrollY - 60))`);
  await t.scrollTo(y);
  await t.shot(`${P}-03-document-check-missing.png`, { description: "Document check scrolled to the missing requirement, what the letter says, and what to ask for.", regions: rd });
  const y2 = await t.eval(`Math.max(0, Math.round((${rd.preview_request_details}).getBoundingClientRect().top + scrollY - 200))`);
  await t.scrollTo(y2);
  await t.shot(`${P}-04-document-check-request-letter.png`, { description: "'Preview the request' expanded: drafted request letter to Lee Morgan at Riverside Outreach.", regions: rd });
  await t.eval(`(${rd.copy_request_button}).click(); true`);
  const copied = await t.waitFor(byText("button", "Copied"), 3000, 100);
  await t.shot(`${P}-04b-document-check-request-copied.png`, { description: `After clicking 'Copy request' (button reads '${copied ? "Copied" : "unchanged"}').`, regions: { ...rd, copied_button: byText("button", "Copied") } });
  await crop(`${P}-04c-crop-request-letter.png`, rd.request_letter_text, 24, "Zoomed crop: drafted request letter to the writer.");
  await crop(`${P}-04d-crop-missing-requirement.png`, `(${rd.missing_requirement_heading}).parentElement`, 24, "Zoomed crop: the missing requirement block (Specific matters relied on, what the letter says, explanation).");
}
const hasAll = await t.eval(`!!(${rd.all_requirements_details})`);
if (hasAll) {
  await t.eval(`(${rd.all_requirements_details}).open = true; true`); await sleep(500);
  const y = await t.eval(`Math.max(0, Math.round((${rd.all_requirements_details}).getBoundingClientRect().top + scrollY - 80))`);
  await t.scrollTo(y);
  await t.shot(`${P}-05-document-check-requirements.png`, { description: `'All 8 requirements for paragraph 17' expanded (${label}).`, regions: rd });
}
await t.shot(`${P}-05-document-check-expanded-full.png`, { full: true, description: `Document check page, full, with details expanded (${label}).`, regions: rd });

// PDF view with marks
await t.goto(`/provider/cases/${C}/documents/${docId}/file`, 2500);
await t.waitFor("document.querySelector('.app-pdf__page canvas') && document.querySelectorAll('.app-pdf__mark').length > 0", 15000);
await sleep(1500);
const rp = { heading: "document.querySelector('h1')", pdf_page: "document.querySelector('.app-pdf__page')", problem_mark: "document.querySelector('.app-pdf__mark--problem')",
  all_marks_first: "document.querySelector('.app-pdf__mark')", findings_panel: "document.querySelector('.app-split__findings')", findings_problem_item: "[...document.querySelectorAll('.app-findings__item')].find(li => li.querySelector('.app-mark__number--problem'))",
  verdict_tag: "document.querySelector('.app-split__findings .govuk-tag')", highlight_key: "document.querySelector('.app-highlight-key')" };
const markBoxes = await t.eval(`[...document.querySelectorAll('.app-pdf__mark')].map((m,i) => ({i, problem: m.classList.contains('app-pdf__mark--problem'), text: m.textContent.trim().slice(0,40)}))`);
console.log("marks", JSON.stringify(markBoxes));
const yp = await t.eval(`Math.max(0, Math.round(document.querySelector('.app-doc-panel').getBoundingClientRect().top + scrollY - 20))`);
await t.scrollTo(yp);
await t.shot(`${P}-06-document-pdf-marks.png`, { description: `Document view: the PDF with numbered marks on each sentence the check relied on, findings list alongside (${label}).`, regions: rp });
if (await t.eval(`!!(${rp.problem_mark})`)) {
  await t.eval(`(${rp.problem_mark}).scrollIntoView({block:'center'}); true`); await sleep(500);
  await t.shot(`${P}-07-document-pdf-problem-mark.png`, { description: "PDF view scrolled to the highlighted problem sentence ('Victim testimony and referral').", regions: rp });
  await crop(`${P}-07b-crop-pdf-problem-sentence.png`, rp.problem_mark, 80, "Zoomed crop: the highlighted problem sentence on the PDF.");
}
await t.shot(`${P}-06-document-pdf-marks-full.png`, { full: true, description: `Document view, full page (${label}).`, regions: rp });
await crop(`${P}-06b-crop-pdf-page.png`, rp.pdf_page, 8, `Zoomed crop: the PDF page with all marks (${label}).`);
t.close(); process.exit(0);
