// The live routes against a mocked back end: failures reach the screen, the Civil Apply
// pack is the real zip, the drop-letter case gets its client's name, and the LAA's own
// check shows on the review.

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { describeFailure, UNSUPPORTED_FILE_MESSAGE } from "../api/backend";
import * as live from "../api/routes";
import { ActionErrorProvider } from "../components/ErrorBanner";
import { ProviderLayout } from "../components/layout";
import { Review } from "../pages/caseworker/Review";
import { CaseDetails } from "../pages/provider/CaseDetails";
import { findCase, queue } from "../sample/cases";

interface Reply {
  status?: number;
  body: unknown;
}
type Handler = (body: unknown) => Reply;
interface Call {
  method: string;
  path: string;
  body: unknown;
}

/** Answers `fetch` by "METHOD /web/path" and records every call. */
function mockApi(handlers: Record<string, Handler>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = init?.method ?? "GET";
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : (init?.body ?? null);
      calls.push({ method, path: url.pathname, body });
      const handler = handlers[`${method} ${url.pathname}`];
      const reply = handler ? handler(body) : { status: 404, body: { detail: `no handler for ${method} ${url.pathname}` } };
      const status = reply.status ?? 200;
      return { ok: status >= 200 && status < 300, status, statusText: "", json: async () => reply.body } as unknown as Response;
    }),
  );
  return calls;
}

/** Records the hidden links the download helpers click instead of navigating. */
function captureDownloads() {
  const clicks: { href: string; download: string }[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    clicks.push({ href: this.href, download: this.download });
  });
  return clicks;
}

function renderLive(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/client/:token" element={<live.ClientUploadRoute />} />
        <Route path="/provider/cases/:caseId/details" element={<live.CaseDetailsRoute />} />
        <Route path="/provider/cases/:caseId/submit" element={<live.CaseSubmitRoute />} />
        <Route path="*" element={<p>Elsewhere</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.scrollTo = vi.fn();
  URL.createObjectURL = vi.fn(() => "blob:summary");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("API failures", () => {
  it("passes the back end's accepted-format message through from a 415", () => {
    const detail = "unsupported file type '.xyz'; use PDF, Word, a photo (JPG, PNG, HEIC), email or text";
    expect(describeFailure(415, detail)).toBe("Unsupported file type '.xyz'; use PDF, Word, a photo (JPG, PNG, HEIC), email or text");
    expect(describeFailure(415, null)).toBe(UNSUPPORTED_FILE_MESSAGE);
    expect(describeFailure(500, "case not found")).toBe("case not found");
    expect(describeFailure(502, null, "Bad Gateway")).toBe("Bad Gateway (502)");
  });

  it("renders the action error as a GOV.UK error summary at the top of the main content", () => {
    render(
      <MemoryRouter>
        <ActionErrorProvider message="This file type is not supported: use PDF, Word or a photo">
          <ProviderLayout firm="Firm">
            <h1>Screen</h1>
          </ProviderLayout>
        </ActionErrorProvider>
      </MemoryRouter>,
    );
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("There is a problem");
    expect(alert.textContent).toContain("This file type is not supported: use PDF, Word or a photo");
    const main = document.getElementById("main-content")!;
    expect(main.firstElementChild?.className).toContain("govuk-error-summary");
  });

  it("shows nothing when no action has failed", () => {
    render(
      <MemoryRouter>
        <ProviderLayout firm="Firm">
          <h1>Screen</h1>
        </ProviderLayout>
      </MemoryRouter>,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows a refused client upload above the screen", async () => {
    mockApi({
      "GET /web/client/tok": () => ({
        body: { firstName: "Jane", firmName: "Hartley & Webb", askLabel: "Letter", linkExpiresAt: "2026-10-12T00:00:00Z", latestDocument: null, state: null },
      }),
      "POST /web/client/tok/upload": () => ({ status: 415, body: { detail: "unsupported file type '.xyz'; use PDF, Word, a photo (JPG, PNG, HEIC), email or text" } }),
    });
    renderLive("/client/tok");
    await screen.findByRole("heading", { level: 1, name: "Send your letter" });
    expect(screen.queryByRole("alert")).toBeNull();

    const input = screen.getByLabelText("Take photos");
    fireEvent.change(input, { target: { files: [new File(["x"], "letter.xyz")] } });

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Unsupported file type '.xyz'; use PDF, Word, a photo (JPG, PNG, HEIC), email or text");
    // Still on the upload screen: the failure did not navigate away.
    expect(screen.getByRole("heading", { level: 1, name: "Send your letter" })).toBeTruthy();
  });
});

describe("Civil Apply export", () => {
  const data = findCase("gc-0142-corrected")!;

  it("downloads the real pack when the submission has an id", async () => {
    const calls = mockApi({
      "GET /web/cases/gc-0142-corrected": () => ({ body: data }),
      "POST /web/cases/gc-0142-corrected/submit": () => ({
        body: { ...data, case: { ...data.case, submissionId: "sub-1", submittedAt: "2026-10-05T10:00:00Z" }, summary: "Summary text", filename: "GC-0142 verification summary.txt" },
      }),
    });
    const clicks = captureDownloads();
    renderLive("/provider/cases/gc-0142-corrected/submit?selected=d-brookfield-2");
    fireEvent.click(await screen.findByRole("button", { name: "Download for Civil Apply" }));

    await waitFor(() => expect(clicks).toHaveLength(1));
    expect(clicks[0].href).toContain("/web/submissions/sub-1/pack.zip");
    expect(clicks[0].download).toBe("GC-0142 submission pack.zip");
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ documentIds: ["d-brookfield-2"], reason: null });
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    await screen.findByText("Your pack for Civil Apply has downloaded");
  });

  it("falls back to the summary text when there is no submission id", async () => {
    mockApi({
      "GET /web/cases/gc-0142-corrected": () => ({ body: data }),
      "POST /web/cases/gc-0142-corrected/submit": () => ({ body: { ...data, summary: "Summary text", filename: "GC-0142 verification summary.txt" } }),
    });
    const clicks = captureDownloads();
    renderLive("/provider/cases/gc-0142-corrected/submit?selected=d-brookfield-2");
    fireEvent.click(await screen.findByRole("button", { name: "Download for Civil Apply" }));

    await waitFor(() => expect(clicks).toHaveLength(1));
    expect(clicks[0].href).toBe("blob:summary");
    expect(clicks[0].download).toBe("GC-0142 verification summary.txt");
  });

  it("shows the failure instead of claiming the pack downloaded", async () => {
    mockApi({
      "GET /web/cases/gc-0142-corrected": () => ({ body: data }),
      "POST /web/cases/gc-0142-corrected/submit": () => ({ status: 409, body: { detail: "This case has already been submitted" } }),
    });
    const clicks = captureDownloads();
    renderLive("/provider/cases/gc-0142-corrected/submit?selected=d-brookfield-2");
    fireEvent.click(await screen.findByRole("button", { name: "Download for Civil Apply" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("This case has already been submitted");
    expect(clicks).toHaveLength(0);
    expect(screen.queryByText("Your pack for Civil Apply has downloaded")).toBeNull();
  });
});

describe("drop-letter onboarding", () => {
  const unnamed = { ...findCase("gc-0142")!, case: { ...findCase("gc-0142")!.case, applicantName: "", otherPartyName: "" } };

  it("requires the client's name and sends it with the other details", () => {
    const onSave = vi.fn();
    render(
      <MemoryRouter>
        <CaseDetails c={unnamed.case} onSave={onSave} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Add your client’s details" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).not.toHaveBeenCalled();
    expect(within(screen.getByRole("alert")).getByText("Enter your client’s full name")).toBeTruthy();
    expect(screen.getByLabelText("Your client’s full name").className).toContain("govuk-input--error");

    fireEvent.change(screen.getByLabelText("Your client’s full name"), { target: { value: "  Jane Doe " } });
    fireEvent.change(screen.getByLabelText("Other party’s full name"), { target: { value: "John Doe" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith({ applicantName: "Jane Doe", otherPartyName: "John Doe", askLabel: unnamed.case.askLabel });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the existing name in the field and the Change details heading", () => {
    render(
      <MemoryRouter>
        <CaseDetails c={findCase("gc-0142")!.case} onSave={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Change details" })).toBeTruthy();
    expect((screen.getByLabelText("Your client’s full name") as HTMLInputElement).value).toBe("Jane Doe");
  });

  it("the route PATCHes the case with the applicant's name and moves on", async () => {
    const calls = mockApi({
      "GET /web/cases/gc-0142": () => ({ body: unnamed }),
      "PATCH /web/cases/gc-0142": (body) => ({ body: { ...unnamed, case: { ...unnamed.case, ...(body as object) } } }),
    });
    renderLive("/provider/cases/gc-0142/details");
    await screen.findByRole("heading", { level: 1, name: "Add your client’s details" });

    fireEvent.change(screen.getByLabelText("Your client’s full name"), { target: { value: "Jane Doe" } });
    fireEvent.change(screen.getByLabelText("Other party’s full name"), { target: { value: "John Doe" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("Elsewhere");
    const patch = calls.find((c) => c.method === "PATCH");
    expect(patch?.body).toEqual({ applicantName: "Jane Doe", otherPartyName: "John Doe", askLabel: unnamed.case.askLabel });
  });

  it("the route shows a failed save instead of moving on", async () => {
    mockApi({
      "GET /web/cases/gc-0142": () => ({ body: unnamed }),
      "PATCH /web/cases/gc-0142": () => ({ status: 500, body: { detail: "Could not save the case" } }),
    });
    renderLive("/provider/cases/gc-0142/details");
    await screen.findByRole("heading", { level: 1, name: "Add your client’s details" });
    fireEvent.change(screen.getByLabelText("Your client’s full name"), { target: { value: "Jane Doe" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Could not save the case");
    expect(screen.queryByText("Elsewhere")).toBeNull();
  });
});

describe("independent LAA check on the review", () => {
  const smith = queue.find((q) => q.case.ref === "GC-0130")!;
  const renderReview = (laaCheck: { done: boolean; differences: number } | null | undefined) =>
    render(
      <MemoryRouter>
        <Review data={{ ...smith, case: { ...smith.case, laaCheck } }} activeDocId={smith.documents[0].id} onDecide={() => {}} />
      </MemoryRouter>,
    );

  it("says when the LAA's check agrees", () => {
    renderReview({ done: true, differences: 0 });
    expect(screen.getByText("Independent LAA check: agrees with the provider’s check")).toBeTruthy();
  });

  it("counts the differences", () => {
    renderReview({ done: true, differences: 2 });
    expect(screen.getByText(/Independent LAA check: 2 differences/)).toBeTruthy();
    cleanup();
    renderReview({ done: true, differences: 1 });
    expect(screen.getByText(/Independent LAA check: 1 difference$/)).toBeTruthy();
  });

  it("shows nothing when there is no LAA check", () => {
    renderReview(undefined);
    expect(screen.queryByText(/Independent LAA check/)).toBeNull();
    cleanup();
    renderReview(null);
    expect(screen.queryByText(/Independent LAA check/)).toBeNull();
  });
});

describe("caseworker queue and review by submission", () => {
  // Two undecided submissions of the same case: the back end gives one queue row each, with its own
  // submissionId and LAA reference. Each row must open and decide its own pack, not the case's latest.
  const base = queue[0];
  const row = (submissionId: string, ref: string) => ({
    ...base,
    case: { ...base.case, ref, submissionId, laaCheck: { done: true, differences: 0 } },
  });
  const rows = [row("sub-1", "L100001"), row("sub-2", "L100002")];

  function renderCaseworker(path: string) {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/caseworker" element={<live.QueueRoute />} />
          <Route path="/caseworker/cases/:caseId" element={<live.ReviewRoute />} />
          <Route path="*" element={<p>Elsewhere</p>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("links each queue row to its own submission", async () => {
    mockApi({ "GET /web/queue": () => ({ body: rows }) });
    renderCaseworker("/caseworker");
    const first = await screen.findByRole("link", { name: "L100001" });
    const second = screen.getByRole("link", { name: "L100002" });
    expect(first.getAttribute("href")).toBe("/caseworker/cases/sub-1");
    expect(second.getAttribute("href")).toBe("/caseworker/cases/sub-2");
    expect(screen.getByRole("button", { name: "Review next case" }).getAttribute("href")).toMatch(/^\/caseworker\/cases\/sub-[12]$/);
  });

  it("decides the submission on screen and sends its id", async () => {
    const calls = mockApi({
      "GET /web/queue/sub-2": () => ({ body: rows[1] }),
      "POST /web/queue/sub-2/decision": (body) => ({
        body: { action: (body as { action: string }).action, note: "", toolVerdict: "meets", agreedWithTool: true, at: "2026-10-05T10:00:00Z", submissionId: "sub-2" },
      }),
      "GET /web/queue": () => ({ body: [] }),
    });
    renderCaseworker("/caseworker/cases/sub-2");
    fireEvent.click(await screen.findByRole("button", { name: "Accept evidence" }));
    await screen.findByText(/for L100002/);
    const post = calls.find((c) => c.method === "POST");
    expect(post?.path).toBe("/web/queue/sub-2/decision");
    expect(post?.body).toMatchObject({ action: "accept", submissionId: "sub-2" });
  });

  it("still opens a sample-style row that has no submission id by its case id", async () => {
    mockApi({ "GET /web/queue": () => ({ body: [base] }) });
    renderCaseworker("/caseworker");
    const link = await screen.findByRole("link", { name: base.case.ref });
    expect(link.getAttribute("href")).toBe(`/caseworker/cases/${base.case.id}`);
  });
});
