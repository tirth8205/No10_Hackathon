// Words shown in the interface. Engine outcomes are mapped to labels in one place.
// Language rules (spec 3.3): never show "approved", "rejected", "pass" or "fail".

import type { CheckResult, ElementStatus } from "./types";

export type TagColour = "green" | "yellow" | "blue" | "grey" | "purple";

export interface Verdict {
  key: "pass" | "fail" | "refer" | "not_prescribed" | "checking" | "none";
  label: string;
  colour: TagColour;
}

export const VERDICTS: Record<Verdict["key"], Verdict> = {
  pass: { key: "pass", label: "Meets the requirements", colour: "green" },
  fail: { key: "fail", label: "Needs a change", colour: "yellow" },
  refer: { key: "refer", label: "Needs a caseworker check", colour: "blue" },
  not_prescribed: { key: "not_prescribed", label: "Not an accepted evidence type", colour: "grey" },
  checking: { key: "checking", label: "Checking", colour: "grey" },
  none: { key: "none", label: "No evidence yet", colour: "grey" },
};

export const ELEMENT_LABELS: Record<ElementStatus, { label: string; colour: TagColour }> = {
  met: { label: "Included", colour: "green" },
  not_met: { label: "Missing", colour: "yellow" },
  unclear: { label: "Unclear", colour: "blue" },
};

export interface Para {
  number: string;
  singular: string;
  plural: string;
  guidance: string;
}

export const PARAS: Record<string, Para> = {
  "1": { number: "1", singular: "Arrest for domestic abuse offence", plural: "Arrest for domestic abuse offences", guidance: "LAA guidance v15, 2.8 to 2.13" },
  "2": { number: "2", singular: "Police caution for DA offence", plural: "Police caution for DA offences", guidance: "LAA guidance v15, 2.14 to 2.17" },
  "3": { number: "3", singular: "Ongoing criminal proceedings", plural: "Ongoing criminal proceedings", guidance: "LAA guidance v15, 2.18 to 2.25" },
  "4": { number: "4", singular: "Conviction for DA offence", plural: "Conviction for DA offences", guidance: "LAA guidance v15, 2.26 to 2.30" },
  "5": { number: "5", singular: "Bind over for DA offence", plural: "Bind over for DA offences", guidance: "LAA guidance v15, 2.31 to 2.33" },
  "6": { number: "6", singular: "Domestic violence protection notice", plural: "Domestic violence protection notices", guidance: "LAA guidance v15, 2.34" },
  "6A": { number: "6A", singular: "Domestic abuse protection notice", plural: "Domestic abuse protection notices", guidance: "LAA guidance v15, 2.35 to 2.37" },
  "7": { number: "7", singular: "Protective injunction", plural: "Protective injunctions", guidance: "LAA guidance v15, 2.38 to 2.42" },
  "8": { number: "8", singular: "Undertaking given by B", plural: "Undertaking given by Bs", guidance: "LAA guidance v15, 2.43 to 2.44" },
  "9": { number: "9", singular: "Finding of fact", plural: "Finding of facts", guidance: "LAA guidance v15, 2.45 to 2.48" },
  "10": { number: "10", singular: "Expert report for court", plural: "Expert report for courts", guidance: "LAA guidance v15, 2.49 to 2.51" },
  "11": { number: "11", singular: "Health professional letter", plural: "Health professional letters", guidance: "LAA guidance v15, 2.52 to 2.58" },
  "12": { number: "12", singular: "Health professional referral", plural: "Health professional referrals", guidance: "LAA guidance v15, 2.61 to 2.65" },
  "13": { number: "13", singular: "MARAC letter", plural: "MARAC letters", guidance: "LAA guidance v15, 2.66 to 2.67" },
  "14": { number: "14", singular: "IDVA letter", plural: "IDVA letters", guidance: "LAA guidance v15, 2.68" },
  "15": { number: "15", singular: "ISVA letter", plural: "ISVA letters", guidance: "LAA guidance v15, 2.69" },
  "16": { number: "16", singular: "Local authority or housing letter", plural: "Local authority or housing letters", guidance: "LAA guidance v15, 2.70 to 2.73" },
  "17": { number: "17", singular: "Support organisation letter", plural: "Support organisation letters", guidance: "LAA guidance v15, 2.74 to 2.77" },
  "18": { number: "18", singular: "Refuge refusal letter", plural: "Refuge refusal letters", guidance: "LAA guidance v15, 2.78 to 2.82" },
  "19": { number: "19", singular: "Public authority letter", plural: "Public authority letters", guidance: "LAA guidance v15, 2.83 to 2.85" },
  "20": { number: "20", singular: "Home Office leave letter", plural: "Home Office leave letters", guidance: "LAA guidance v15, 2.86" },
  "21": { number: "21", singular: "Economic abuse evidence", plural: "Economic abuse evidences", guidance: "LAA guidance v15, 2.87 to 2.93" },
};

export function docVerdict(result: CheckResult | null): Verdict {
  if (!result) return VERDICTS.checking;
  if (result.outcome === "refer") return VERDICTS.refer;
  if (result.matchedPara === null) return VERDICTS.not_prescribed;
  return VERDICTS[result.outcome];
}

/** One document that meets the requirements is enough (docs 7.2, step 9). */
export function caseVerdict(results: (CheckResult | null)[]): Verdict {
  const keys = results.map((r) => docVerdict(r).key);
  for (const key of ["pass", "refer", "fail"] as const) {
    if (keys.includes(key)) return VERDICTS[key];
  }
  if (keys.includes("checking")) return VERDICTS.checking;
  return VERDICTS.none;
}

export function paraOf(result: CheckResult | null): Para | null {
  if (!result?.matchedPara) return null;
  return PARAS[result.matchedPara] ?? null;
}

/** What the tool's verdict suggests the caseworker does, for the agreement log. */
export function suggestedAction(verdict: Verdict): "accept" | "return" | "refer" {
  if (verdict.key === "pass") return "accept";
  if (verdict.key === "refer") return "refer";
  return "return";
}
