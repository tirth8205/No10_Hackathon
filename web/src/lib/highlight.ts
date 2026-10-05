// Splits document text into plain and highlighted segments, so the caseworker can
// see each quote the check relied on in context. Numbers match the requirement list.

import type { ElementResult } from "./types";

export interface Segment {
  text: string;
  mark?: { number: number; problem: boolean };
}

interface Range {
  start: number;
  end: number;
  number: number;
  problem: boolean;
}

function find(text: string, quote: string): number {
  const exact = text.indexOf(quote);
  if (exact >= 0) return exact;
  return text.toLowerCase().indexOf(quote.toLowerCase());
}

export function highlight(text: string, elements: ElementResult[]): Segment[] {
  const ranges: Range[] = [];
  elements.forEach((el, i) => {
    if (!el.quote) return;
    const start = find(text, el.quote);
    if (start < 0) return;
    ranges.push({ start, end: start + el.quote.length, number: i + 1, problem: el.status !== "met" });
  });
  ranges.sort((a, b) => a.start - b.start);

  const segments: Segment[] = [];
  let cursor = 0;
  for (const r of ranges) {
    if (r.start < cursor) continue; // overlapping quote: keep the first
    if (r.start > cursor) segments.push({ text: text.slice(cursor, r.start) });
    segments.push({ text: text.slice(r.start, r.end), mark: { number: r.number, problem: r.problem } });
    cursor = r.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}
