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
  "7": { number: "7", singular: "Protective injunction", plural: "Protective injunctions", guidance: "LAA guidance v15, 2.38 to 2.42" },
  "11": { number: "11", singular: "Health professional letter", plural: "Health professional letters", guidance: "LAA guidance v15, 2.52 to 2.58" },
  "13": { number: "13", singular: "MARAC letter", plural: "MARAC letters", guidance: "LAA guidance v15, 2.66 to 2.67" },
  "14": { number: "14", singular: "IDVA letter", plural: "IDVA letters", guidance: "LAA guidance v15, 2.68" },
  "16": { number: "16", singular: "Local authority or housing letter", plural: "Local authority or housing letters", guidance: "LAA guidance v15, 2.70 to 2.73" },
  "17": { number: "17", singular: "Support organisation letter", plural: "Support organisation letters", guidance: "LAA guidance v15, 2.74 to 2.77" },
  "18": { number: "18", singular: "Refuge refusal letter", plural: "Refuge refusal letters", guidance: "LAA guidance v15, 2.78 to 2.82" },
  "19": { number: "19", singular: "Public authority letter", plural: "Public authority letters", guidance: "LAA guidance v15, 2.83 to 2.85" },
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
