import { openTab, DESKTOP, byText, sleep } from "./cdp.mjs";
const SID = process.argv[2];
const t = await openTab(); await t.setViewport(DESKTOP);
await t.goto("/caseworker", 2500);
const rq = { heading: "document.querySelector('h1')", jane_row: byText("tr", "Jane Doe"), queue_table: "document.querySelector('table')", review_next_button: byText("a.govuk-button, button", "Review next") };
await t.shot("c01-caseworker-queue.png", { description: "LAA caseworker evidence queue (reference). Jane Doe L597743 listed as Meets the requirements, 3 of 3 checks agreed.", regions: rq });
await t.shot("c01-caseworker-queue-full.png", { full: true, description: "Caseworker queue, full page.", regions: rq });
await t.goto(`/caseworker/cases/${SID}`, 2500);
await t.waitFor("document.querySelector('.app-pdf__page canvas') && document.querySelectorAll('.app-pdf__mark').length > 0", 15000); await sleep(1500);
const rr = { heading: "document.querySelector('h1')", verdict: byText("p, div, span", "Tool verdict"), pdf_page: "document.querySelector('.app-pdf__page')", specific_matters_mark: "document.querySelectorAll('.app-pdf__mark')[6]",
  independent_check: byText(".govuk-inset-text, .govuk-warning-text", "Independent LAA check"), findings: "document.querySelector('.app-split__findings') || document.querySelector('.app-findings')",
  verifying_author: byText("h2, h3", "Verifying the author"), decision_heading: byText("h2, legend", "Your decision"), accept_button: byText("button", "Accept evidence") };
await t.shot("c02-caseworker-review.png", { description: "Caseworker review page for Jane Doe (L597743): embedded PDF with numbered marks, tool verdict, findings (reference).", regions: rr });
const y = await t.eval(`Math.max(0, Math.round(document.querySelector('.app-pdf').getBoundingClientRect().top + scrollY - 120))`);
await t.scrollTo(y);
await t.shot("c02-caseworker-review-pdf.png", { description: "Caseworker review scrolled to the embedded PDF with highlights and the findings list; independent LAA check agrees.", regions: rr });
await t.shot("c02-caseworker-review-full.png", { full: true, description: "Caseworker review page, full (includes author verification and decision buttons).", regions: rr });
t.close(); process.exit(0);
