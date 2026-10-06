// The uploaded PDF itself, rendered page by page, with each quote the check relied on
// marked on the page. The marks come from the PDF's own text layer (pdf.js text items),
// so they land on the real letter rather than on a transcript of it. A scanned PDF has no
// text layer; it is shown as is and the caller falls back to the highlighted text.

import { useEffect, useRef, useState } from "react";
import type { ElementResult } from "../lib/types";

interface Mark {
  left: number;
  top: number;
  width: number;
  height: number;
  number: number;
  problem: boolean;
  /** The first box of a quote carries the number badge. */
  badge: boolean;
  /** How many earlier badges sit at the same spot (two requirements resting on one line); shifts this one left. */
  stack: number;
}

interface PageView {
  width: number;
  height: number;
  marks: Mark[];
  /** The page had a text layer. */
  hasText: boolean;
}

interface TextItemLike {
  str: string;
  transform: number[];
  width: number;
  height: number;
}

/** Same normalisation as the verifier, loosely: case, quote marks, dashes, runs of whitespace. */
function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/[‘’‚′]/g, "'")
    .replace(/[“”„″]/g, '"')
    .replace(/[‐-―−]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

/** Which text items a quote covers on a page. Fragments of a stitched quote ("... ") are found separately. */
export function locate(items: TextItemLike[], quote: string): number[][] {
  // One string for the page with a space between items, remembering which item each character came from.
  let page = "";
  const owner: number[] = [];
  items.forEach((item, i) => {
    const s = norm(item.str);
    if (!s) return;
    if (page) {
      page += " ";
      owner.push(-1);
    }
    page += s;
    for (let k = 0; k < s.length; k++) owner.push(i);
  });
  const found: number[][] = [];
  for (const fragment of quote.split("...").map(norm).filter((f) => f.length >= 3)) {
    let start = page.indexOf(fragment);
    let length = fragment.length;
    if (start < 0 && fragment.length > 40) {
      // Hyphenation or a line break inside the quote: settle for its opening words.
      const head = fragment.slice(0, 40);
      start = page.indexOf(head);
      length = head.length;
    }
    if (start < 0) continue;
    const covered = [...new Set(owner.slice(start, start + length).filter((i) => i >= 0))];
    if (covered.length) found.push(covered);
  }
  return found;
}

export function PdfView({ url, elements, onTextLayer }: { url: string; elements: ElementResult[]; onTextLayer?: (hasText: boolean) => void }) {
  const container = useRef<HTMLDivElement>(null);
  const canvases = useRef<(HTMLCanvasElement | null)[]>([]);
  const [pages, setPages] = useState<PageView[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // The legacy build carries polyfills: the modern one needs Uint8Array.prototype.toHex (Chrome 140,
        // Safari 18.2), so any older browser at a demo would show no letter at all.
        const pdfjs = await import("pdfjs-dist/legacy/build/pdf.mjs");
        const worker = await import("pdfjs-dist/legacy/build/pdf.worker.min.mjs?url");
        pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
        const doc = await pdfjs.getDocument({ url }).promise;
        const width = Math.max(320, container.current?.clientWidth ?? 640);
        const dpr = window.devicePixelRatio || 1;
        const views: PageView[] = [];
        const renders: (() => Promise<void>)[] = [];
        for (let n = 1; n <= doc.numPages; n++) {
          const page = await doc.getPage(n);
          const scale = Math.min(2, width / page.getViewport({ scale: 1 }).width);
          const viewport = page.getViewport({ scale });
          const content = await page.getTextContent();
          const items: TextItemLike[] = content.items.flatMap((it) =>
            "str" in it ? [{ str: it.str, transform: it.transform, width: it.width, height: it.height }] : [],
          );
          const marks: Mark[] = [];
          elements.forEach((el, i) => {
            if (!el.quote) return;
            locate(items, el.quote).forEach((covered, f) => {
              covered.forEach((idx, k) => {
                const item = items[idx];
                const tx = pdfjs.Util.transform(viewport.transform, item.transform);
                const h = (item.height || Math.hypot(tx[2], tx[3]) / scale) * scale;
                marks.push({
                  left: tx[4] - 1,
                  top: tx[5] - h - 1,
                  width: item.width * scale + 2,
                  height: h + 3,
                  number: i + 1,
                  problem: el.status !== "met",
                  badge: f === 0 && k === 0,
                  stack: 0,
                });
              });
            });
          });
          // Requirements that rest on the same line would put their badges on top of each other: set them side by side.
          const used = new Map<string, number>();
          for (const m of marks) {
            if (!m.badge) continue;
            const spot = `${Math.round(m.left)}:${Math.round(m.top)}`;
            m.stack = used.get(spot) ?? 0;
            used.set(spot, m.stack + 1);
          }
          views.push({ width: viewport.width, height: viewport.height, marks, hasText: items.some((it) => it.str.trim()) });
          const index = n - 1;
          renders.push(async () => {
            const canvas = canvases.current[index];
            if (!canvas) return;
            canvas.width = Math.floor(viewport.width * dpr);
            canvas.height = Math.floor(viewport.height * dpr);
            canvas.style.width = `${viewport.width}px`;
            canvas.style.height = `${viewport.height}px`;
            const ctx = canvas.getContext("2d");
            if (!ctx) return;
            await page.render({ canvas, canvasContext: ctx, viewport, transform: dpr === 1 ? undefined : [dpr, 0, 0, dpr, 0, 0] }).promise;
          });
        }
        if (cancelled) return;
        setPages(views);
        onTextLayer?.(views.some((v) => v.hasText));
        // The canvases exist once React has laid out the pages.
        requestAnimationFrame(() => {
          if (!cancelled) void Promise.all(renders.map((r) => r()));
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  if (error) {
    return (
      <p className="govuk-body">
        The document could not be displayed here.{" "}
        <a className="govuk-link" href={url} target="_blank" rel="noreferrer">
          Open it in a new tab
        </a>
        .
      </p>
    );
  }
  return (
    <div ref={container} className="app-pdf">
      {!pages && (
        <p className="govuk-body" role="status">
          <span className="app-spinner" aria-hidden="true" />
          Loading the document
        </p>
      )}
      {pages?.map((p, i) => (
        <div key={i} className="app-pdf__page" style={{ width: p.width, height: p.height }}>
          <canvas
            ref={(el) => {
              canvases.current[i] = el;
            }}
            aria-label={`Page ${i + 1} of the document`}
          />
          {p.marks.map((m, k) => (
            <div
              key={k}
              className={m.problem ? "app-pdf__mark app-pdf__mark--problem" : "app-pdf__mark"}
              style={{ left: m.left, top: m.top, width: m.width, height: m.height }}
              aria-hidden="true"
            >
              {m.badge && (
                <span
                  className={m.problem ? "app-mark__number app-mark__number--problem app-pdf__badge" : "app-mark__number app-pdf__badge"}
                  style={m.stack ? { left: -26 - m.stack * 24 } : undefined}
                >
                  {m.number}
                </span>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
