import { highlight } from "../lib/highlight";
import type { ElementResult } from "../lib/types";

/** The document's text with each quote the check relied on highlighted and numbered. */
export function DocumentText({ text, elements }: { text: string; elements: ElementResult[] }) {
  const segments = highlight(text, elements);
  return (
    <div className="app-document">
      {segments.map((segment, i) =>
        segment.mark ? (
          <mark key={i} className={segment.mark.problem ? "app-mark app-mark--problem" : "app-mark"}>
            <span className="app-mark__number" aria-hidden="true">
              {segment.mark.number}
            </span>
            <span className="govuk-visually-hidden">
              {segment.mark.problem ? `Wording that needs a change, requirement ${segment.mark.number}: ` : `Requirement ${segment.mark.number}: `}
            </span>
            {segment.text}
          </mark>
        ) : (
          <span key={i}>{segment.text}</span>
        ),
      )}
    </div>
  );
}

export function HighlightKey() {
  return (
    <ul className="govuk-list govuk-body-s app-highlight-key">
      <li>
        <span className="app-mark app-highlight-key__swatch" aria-hidden="true" /> Sentence the check relied on
      </li>
      <li>
        <span className="app-mark app-mark--problem app-highlight-key__swatch" aria-hidden="true" /> Wording that needs a change
      </li>
    </ul>
  );
}
