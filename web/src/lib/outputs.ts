// Text the service drafts for people to edit and send. Templated from the check
// result so the content is predictable (spec 10.1, step 8).

import { documentTitle } from "./evidence";
import { longDate } from "./dates";
import { docVerdict, paraOf } from "./labels";
import type { Case, CaseDocument, CheckResult } from "./types";

const SAMPLE_LETTERS = "https://www.gov.uk/government/collections/sample-letters-to-get-evidence-of-domestic-violence";

const gaps = (r: CheckResult) => r.elements.filter((e) => e.status !== "met");

export interface ClientMessage {
  title: string;
  body: string;
  addTitle?: string;
  addBody?: string;
}

/** What the client sees after an upload. Plain words, no legal reasoning, no blame. */
export function clientMessage(result: CheckResult): ClientMessage {
  const verdict = docVerdict(result).key;
  if (verdict === "pass") {
    return { title: "Your letter is ready", body: "It meets the requirements." };
  }
  if (verdict === "fail") {
    const missing = gaps(result);
    const hints = missing.map((e) => e.clientHint).filter(Boolean) as string[];
    return {
      title: missing.length === 1 ? "Your letter needs one change" : "Your letter needs a few changes",
      body: "Nothing is wrong with your case. The letter just needs a bit more detail.",
      addTitle: "What to add",
      addBody: hints.join(" ") || "Your solicitor will tell you what is needed.",
    };
  }
  if (verdict === "not_prescribed") {
    return { title: "Thank you", body: "This can’t be used on its own, but your solicitor can see it." };
  }
  return {
    title: "Your solicitor will check this",
    body: "We couldn’t check everything straight away. Your solicitor will look at it and tell you if anything else is needed.",
  };
}

/** The message the client sees, as one line for the solicitor's timeline. */
export function clientMessageLine(result: CheckResult): string {
  const m = clientMessage(result);
  return [m.title + ".", m.body, m.addBody].filter(Boolean).join(" ");
}

/** The asks to the letter writer, one per missing requirement, each written to the writer. */
function asks(r: CheckResult): string[] {
  return gaps(r)
    .map((e) => e.fix)
    .filter((fix): fix is string => Boolean(fix));
}

const changeWord = (n: number) => (n === 1 ? "one change" : `${n} changes`);
const asList = (items: string[]) => (items.length === 1 ? items[0] : items.map((a) => `- ${a}`).join("\n"));

/** Request to the letter writer, from the solicitor. */
export function requestLetter(c: Case, doc: CaseDocument): string {
  const r = doc.result;
  if (!r) return "";
  const para = paraOf(r);
  const list = asks(r);
  const to = [r.authorName, r.authorOrg].filter(Boolean).join(", ");
  const dated = r.letterDate ? ` of ${longDate(r.letterDate)}` : "";
  return [
    `To: ${to}`,
    "",
    `Dear ${r.authorName ?? "Sir or Madam"},`,
    "",
    `Thank you for your letter${dated} supporting our client, ${c.applicantName}.`,
    "",
    `For legal aid, the letter needs ${changeWord(list.length)} (Civil Legal Aid (Procedure) Regulations 2012, Schedule 1${para ? `, paragraph ${para.number}` : ""}):`,
    "",
    asList(list),
    "",
    `Could you reissue the letter with this added? The rest of the letter can stay as it is. There is sample wording at ${SAMPLE_LETTERS}`,
    "",
    "Kind regards,",
    c.firm,
  ].join("\n");
}

/** A shorter message the client can send to the letter writer themselves. */
export function clientRequestMessage(c: Case, doc: CaseDocument): string {
  const r = doc.result;
  if (!r) return "";
  const list = asks(r);
  return [
    `Hello${r.authorName ? ` ${r.authorName}` : ""},`,
    "",
    `Thank you for the letter you wrote for me. My solicitor says it needs ${changeWord(list.length)} before it can be used:`,
    "",
    asList(list),
    "",
    "Could you send me an updated letter? Everything else can stay the same.",
    "",
    "Thank you,",
    firstName(c),
  ].join("\n");
}

/** The firm's name as a client would say it, for example "Hartley & Webb". */
export function firmShortName(firm: string): string {
  return firm.replace(/\s+(Solicitors|LLP|Ltd)$/i, "");
}

/** Caseworker's return note, drafted from the missing requirements in every submitted document. */
export function returnNote(c: Case, docs: CaseDocument[]): string {
  const sections = docs
    .filter((d) => d.result && docVerdict(d.result).key !== "pass")
    .map((d, i) => {
      const r = d.result!;
      const para = paraOf(r);
      const heading = `${i + 1}. ${documentTitle(d)}${para ? ` (Schedule 1, paragraph ${para.number})` : ""}`;
      const lines = gaps(r).map((e) => e.explanation);
      return [heading, ...lines].join("\n");
    });
  const several = sections.length > 1;
  return [
    `Dear ${c.firm},`,
    "",
    `We cannot accept the domestic abuse evidence for ${c.applicantName} (${c.ref}) yet.`,
    "",
    sections.join("\n\n"),
    "",
    several ? "You only need one of these letters to be corrected." : "Please provide a corrected letter.",
    `There are sample letters on GOV.UK: ${SAMPLE_LETTERS}`,
  ].join("\n");
}

/** Draft reply to an evidence-check inbox query. */
export function inboxReply(firm: string, docs: CaseDocument[]): string {
  const parts = docs.map((d) => {
    const r = d.result;
    if (!r) return "";
    const para = paraOf(r);
    const name = `${d.pages[0]?.filename ?? "The document"}${para ? ` (Schedule 1, paragraph ${para.number})` : ""}`;
    const verdict = docVerdict(r).key;
    if (verdict === "pass") return `${name}: this meets the requirements.`;
    if (verdict === "not_prescribed") return `${name}: this is not one of the accepted evidence types.`;
    if (verdict === "refer") return `${name}: we need to check this further. ${r.reason}`;
    const missing = gaps(r).map((e) => e.explanation).join(" ");
    const met = r.elements.filter((e) => e.status === "met").map((e) => e.label.toLowerCase());
    return [
      `${name}: this does not yet meet the requirements. ${missing}`,
      met.length ? `The rest of the letter meets the requirements (${met.join("; ")}).` : "",
    ]
      .filter(Boolean)
      .join("\n\n");
  });
  return [
    `Dear ${firm || "colleague"},`,
    "",
    "Thank you for your query about the domestic abuse evidence.",
    "",
    parts.join("\n\n"),
    "",
    `There is sample wording on GOV.UK: ${SAMPLE_LETTERS}`,
    "",
    "Kind regards,",
    "Gateway Evidence Check team",
  ].join("\n");
}

/** Verification summary attached to the submission in Civil Apply. */
export function verificationSummary(c: Case, docs: CaseDocument[]): string {
  const blocks = docs.map((d) => {
    const r = d.result;
    if (!r) return `${documentTitle(d)}: still being checked`;
    const para = paraOf(r);
    const rows = r.elements.map(
      (e) => `  [${e.status === "met" ? "x" : " "}] ${e.label}${e.quote ? `\n      "${e.quote}"` : ""}`,
    );
    return [
      `${documentTitle(d)}`,
      `  Evidence type: ${para ? `${para.singular} (Schedule 1, paragraph ${para.number})` : "Not matched"}`,
      `  Result: ${docVerdict(r).label}`,
      `  Agreement: ${r.agreement}`,
      ...rows,
    ].join("\n");
  });
  return [
    "GATEWAY CHECK – VERIFICATION SUMMARY (PROTOTYPE, SYNTHETIC DATA)",
    "",
    `Client: ${c.applicantName}`,
    `Other party: ${c.otherPartyName}`,
    `Case: ${c.ref}`,
    `Firm: ${c.firm}`,
    "",
    ...blocks,
    "",
    "This summary supports the caseworker's decision. The decision is theirs.",
  ].join("\n");
}

/** Client screens show the first name only. */
export function firstName(c: Case): string {
  return c.applicantName.split(" ")[0] ?? "";
}
