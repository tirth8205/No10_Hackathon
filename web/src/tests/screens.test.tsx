import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router";
import { App } from "../App";

afterEach(cleanup);

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

const SCREENS: [string, string][] = [
  ["/", "Gateway Check screens"],
  ["/how-the-check-works", "How the check works"],
  ["/client/jd7k4q", "Send your letter"],
  ["/client/jd7k4q/checking", "Checking your document"],
  ["/client/jd7k4q/result/change", "Your letter needs one change"],
  ["/client/jd7k4q/result/ready", "Your letter is ready"],
  ["/client/jd7k4q/result/check", "Your solicitor will check this"],
  ["/client/jd7k4q/result/other", "Thank you"],
  ["/client/unknown", "This link no longer works"],
  ["/provider", "Cases"],
  ["/provider/new", "Get an upload link for your client"],
  ["/provider/cases/gc-0142", "Jane Doe"],
  ["/provider/cases/gc-0142-corrected", "Jane Doe"],
  ["/provider/cases/gc-0142-corrected/client", "Jane Doe"],
  ["/provider/cases/gc-0142-corrected/details", "Change details"],
  ["/provider/cases/gc-0142/documents/d-brookfield-1", "Letter from Brookfield, 28 September"],
  ["/provider/cases/gc-0142-corrected/documents/d-brookfield-2", "Letter from Brookfield, 5 October"],
  ["/provider/cases/gc-0142/documents/d-gp/file", "GP letter, 22 September"],
  ["/provider/cases/gc-0142-corrected/submit?selected=d-brookfield-2", "Check what you’re submitting"],
  ["/provider/cases/gc-0145", "John Smith"],
  ["/caseworker", "Evidence queue"],
  ["/caseworker/cases/gc-0130", "Jane Smith v Mark Smith"],
  ["/caseworker/cases/gc-0134", "Jane Roe v Richard Roe"],
  ["/caseworker/inbox", "Draft a reply"],
  ["/caseworker/inbox?state=drafted", "Draft a reply"],
  ["/nowhere", "Page not found"],
];

describe("every screen renders", () => {
  it.each(SCREENS)("%s", (path, heading) => {
    renderAt(path);
    expect(screen.getByRole("heading", { level: 1, name: heading })).toBeTruthy();
  });
});

describe("client safety", () => {
  it("has Exit this page and no service name or navigation", () => {
    renderAt("/client/jd7k4q");
    expect(screen.getByRole("button", { name: /Exit this page/ })).toBeTruthy();
    expect(screen.queryByText("Gateway Check")).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Menu" })).toBeNull();
  });

  it("uses a neutral page title", () => {
    renderAt("/client/jd7k4q");
    expect(document.title).toBe("Upload documents");
  });
});

describe("solicitor evidence", () => {
  it("suggests the corrected letter and keeps the older version", () => {
    renderAt("/provider/cases/gc-0142-corrected");
    expect(screen.getByText("Suggested")).toBeTruthy();
    expect(screen.getByText("Older version.")).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: /Letter from Brookfield, 5 October/ })).toHaveProperty("checked", true);
    expect(screen.getByRole("checkbox", { name: /Letter from Brookfield, 28 September/ })).toHaveProperty("checked", false);
  });

  it("shows the return figure as a minimum", () => {
    renderAt("/provider/cases/gc-0142/documents/d-brookfield-1");
    const banner = screen.getByRole("region", { name: "Getting paid" });
    expect(within(banner).getByText("At least")).toBeTruthy();
    expect(within(banner).getByText("23")).toBeTruthy();
  });
});

describe("caseworker review", () => {
  it("drafts a return note and gives the three decisions equal weight", () => {
    renderAt("/caseworker/cases/gc-0130");
    expect((screen.getByLabelText("Return note") as HTMLTextAreaElement).value).toContain("Mark Smith");
    for (const name of ["Return with note", "Accept evidence", "Refer to senior caseworker"]) {
      expect(screen.getByRole("button", { name }).className).toContain("govuk-button--secondary");
    }
  });
});
