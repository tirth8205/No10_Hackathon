// Groups a case's documents for the solicitor's Evidence tab: by evidence type and
// source, with newer and older versions linked, alternatives marked, and the
// strongest document suggested. One document that meets the requirements is enough.

import { dayMonth } from "./dates";
import { docVerdict, paraOf, type Verdict } from "./labels";
import type { CaseDocument } from "./types";

export type RelationKind = "newer" | "older" | "alternative";

export interface EvidenceItem {
  doc: CaseDocument;
  title: string;
  verdict: Verdict;
  suggested: boolean;
  relation: { kind: RelationKind; label: string; text: string } | null;
}

export interface EvidenceGroup {
  key: string;
  heading: string;
  subheading: string;
  items: EvidenceItem[];
}

const pretty = (filename: string) =>
  filename
    .replace(/\.[a-z0-9]+$/i, "")
    .replace(/\s*\(\d+\)$/, "")
    .replace(/[-_]+/g, " ")
    .replace(/^\w/, (c) => c.toUpperCase());

export function documentTitle(doc: CaseDocument): string {
  const r = doc.result;
  if (!r) return pretty(doc.pages[0]?.filename ?? "Document");
  const date = r.letterDate ? `, ${dayMonth(r.letterDate)}` : "";
  if (r.matchedPara === "11" && r.authorRole?.toLowerCase().includes("general practitioner")) {
    return `GP letter${date}`;
  }
  if (r.shortOrg) return `Letter from ${r.shortOrg}${date}`;
  return pretty(doc.pages[0]?.filename ?? "Document");
}

const sortDate = (doc: CaseDocument) => doc.result?.letterDate ?? doc.uploadedAt;
const newestFirst = (a: CaseDocument, b: CaseDocument) => sortDate(b).localeCompare(sortDate(a));

/** The latest document that meets the requirements, if any. */
export function suggestedDocument(docs: CaseDocument[]): CaseDocument | null {
  const passing = docs.filter((d) => docVerdict(d.result).key === "pass").sort(newestFirst);
  return passing[0] ?? null;
}

export function defaultSelection(docs: CaseDocument[]): string[] {
  const s = suggestedDocument(docs);
  return s ? [s.id] : [];
}

function groupKey(doc: CaseDocument): string {
  const r = doc.result;
  if (!r) return "checking";
  if (!r.matchedPara) return "other";
  return `${r.matchedPara}|${r.authorOrg ?? ""}`;
}

export function groupEvidence(docs: CaseDocument[]): EvidenceGroup[] {
  const suggested = suggestedDocument(docs);
  const byKey = new Map<string, CaseDocument[]>();
  for (const doc of docs) {
    const key = groupKey(doc);
    byKey.set(key, [...(byKey.get(key) ?? []), doc]);
  }

  const prescribedKeys = [...byKey.keys()].filter((k) => k !== "other" && k !== "checking");
  const primaryKey = suggested
    ? groupKey(suggested)
    : prescribedKeys.sort((a, b) => newestFirst(byKey.get(a)![0], byKey.get(b)![0]))[0];
  const primaryOrg = primaryKey ? byKey.get(primaryKey)?.[0].result?.shortOrg : null;

  const order = [
    ...(byKey.has("checking") ? ["checking"] : []),
    ...(primaryKey ? [primaryKey] : []),
    ...prescribedKeys.filter((k) => k !== primaryKey),
    ...(byKey.has("other") ? ["other"] : []),
  ];

  return order.map((key) => {
    const groupDocs = [...byKey.get(key)!].sort(newestFirst);
    const first = groupDocs[0];
    const para = paraOf(first.result);

    const items = groupDocs.map((doc, i): EvidenceItem => {
      let relation: EvidenceItem["relation"] = null;
      const letterDate = (d: CaseDocument) => (d.result?.letterDate ? dayMonth(d.result.letterDate) : "an earlier date");
      if (para && groupDocs.length > 1) {
        relation =
          i === 0
            ? { kind: "newer", label: "Newer version.", text: `Replaces the letter of ${letterDate(groupDocs[1])}.` }
            : { kind: "older", label: "Older version.", text: `Replaced by the letter of ${letterDate(first)}.` };
      } else if (para && key !== primaryKey && primaryOrg) {
        relation = {
          kind: "alternative",
          label: "Alternative.",
          text: `A different type of evidence from the ${primaryOrg} letters. You only need one.`,
        };
      }
      return {
        doc,
        title: documentTitle(doc),
        verdict: docVerdict(doc.result),
        suggested: suggested?.id === doc.id,
        relation,
      };
    });

    if (key === "checking") {
      return { key, heading: "Being checked", subheading: "This usually takes about 20 seconds.", items };
    }
    if (key === "other") {
      return {
        key,
        heading: "Other documents",
        subheading: "Not matched to an accepted evidence type. They stay on your file.",
        items,
      };
    }
    return {
      key,
      heading: para?.plural ?? "Documents",
      subheading: [first.result?.authorOrg, para ? `Schedule 1, paragraph ${para.number}` : null]
        .filter(Boolean)
        .join(" · "),
      items,
    };
  });
}

export type SelectionState = "good" | "risky" | "none";

export function selectionState(docs: CaseDocument[], selectedIds: string[]): SelectionState {
  const selected = docs.filter((d) => selectedIds.includes(d.id));
  if (selected.length === 0) return "none";
  return selected.some((d) => docVerdict(d.result).key === "pass") ? "good" : "risky";
}
