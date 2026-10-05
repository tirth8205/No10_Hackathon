import { describe, expect, it } from "vitest";
import { defaultSelection, groupEvidence, selectionState, suggestedDocument } from "../lib/evidence";
import { highlight } from "../lib/highlight";
import { caseVerdict, docVerdict } from "../lib/labels";
import { clientMessage, inboxReply, requestLetter, returnNote } from "../lib/outputs";
import { janeDoe, janeDoeCorrected, queue } from "../sample/cases";
import { SAMPLE_LETTERS } from "../sample/letters";

describe("sample letters", () => {
  it.each(SAMPLE_LETTERS.map((l) => [l.id, l]))("%s: every quote appears word for word in the letter", (_, l) => {
    for (const e of l.result.elements) {
      if (e.quote) expect(l.text).toContain(e.quote);
    }
  });

  it("never uses banned words in client messages", () => {
    for (const l of SAMPLE_LETTERS) {
      const m = clientMessage(l.result);
      const text = [m.title, m.body, m.addTitle, m.addBody].join(" ").toLowerCase();
      for (const word of ["rejected", "fail", "approved", "not a victim"]) expect(text).not.toContain(word);
    }
  });
});

describe("evidence", () => {
  it("suggests nothing before the corrected letter arrives", () => {
    expect(suggestedDocument(janeDoe.documents)).toBeNull();
    expect(defaultSelection(janeDoe.documents)).toEqual([]);
    expect(caseVerdict(janeDoe.documents.map((d) => d.result)).label).toBe("Needs a change");
  });

  it("links newer and older versions and marks alternatives", () => {
    const groups = groupEvidence(janeDoeCorrected.documents);
    expect(groups.map((g) => g.heading)).toEqual(["Support organisation letters", "Health professional letters", "Other documents"]);

    const [support, health, other] = groups;
    expect(support.items.map((i) => i.doc.id)).toEqual(["d-brookfield-2", "d-brookfield-1"]);
    expect(support.items[0].suggested).toBe(true);
    expect(support.items[0].relation?.text).toBe("Replaces the letter of 28 September.");
    expect(support.items[1].relation?.text).toBe("Replaced by the letter of 5 October.");
    expect(health.items[0].relation?.kind).toBe("alternative");
    expect(other.items[0].verdict.label).toBe("Not an accepted evidence type");
  });

  it("works out the payment state from the selection", () => {
    const docs = janeDoeCorrected.documents;
    expect(selectionState(docs, [])).toBe("none");
    expect(selectionState(docs, ["d-brookfield-1", "d-gp"])).toBe("risky");
    expect(selectionState(docs, ["d-brookfield-1", "d-brookfield-2"])).toBe("good");
  });
});

describe("verdicts", () => {
  it("one document that meets the requirements is enough", () => {
    expect(caseVerdict(janeDoeCorrected.documents.map((d) => d.result)).key).toBe("pass");
  });

  it("maps a refer to a caseworker check, even with a paragraph", () => {
    const idva = queue.find((q) => q.case.ref === "GC-0135")!.documents[0];
    expect(docVerdict(idva.result).label).toBe("Needs a caseworker check");
  });
});

describe("highlight", () => {
  it("numbers quotes in requirement order and marks problem wording", () => {
    const doc = queue.find((q) => q.case.ref === "GC-0130")!.documents[0];
    const marks = highlight(doc.text, doc.result!.elements).filter((s) => s.mark);
    expect(marks.map((m) => m.mark!.number)).toEqual([1, 2, 3, 4]);
    expect(marks.at(-1)).toMatchObject({ text: "might be consistent with", mark: { problem: true } });
  });
});

describe("drafted text", () => {
  it("asks the letter writer for exactly what is missing", () => {
    const vague = janeDoe.documents.find((d) => d.id === "d-brookfield-1")!;
    const letter = requestLetter(janeDoe.case, vague);
    expect(letter).toContain("Dear Sam Taylor,");
    expect(letter).toContain("Please describe the specific matters you relied on");
    expect(letter).toContain("Schedule 1, paragraph 17");
  });

  it("covers every submitted document that needs a change in the return note", () => {
    const smith = queue.find((q) => q.case.ref === "GC-0130")!;
    const note = returnNote(smith.case, smith.documents);
    expect(note).toContain("paragraph 11");
    expect(note).toContain("paragraph 18");
    expect(note).toContain("You only need one of these letters to be corrected.");
  });

  it("drafts an inbox reply naming the problem wording", () => {
    const smith = queue.find((q) => q.case.ref === "GC-0130")!;
    expect(inboxReply("Northgate Family Law", smith.documents.slice(0, 1))).toContain("might be consistent with");
  });
});
