import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { App } from "../App";
import { formatClientCode, normaliseClientCode } from "../lib/clientCode";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

/** Pretend the screen is a desktop (fine pointer, wide window) or a phone. */
function stubScreen(phone: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: phone,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

describe("client code", () => {
  it("formats and normalises codes", () => {
    expect(formatClientCode("K7QM4XPR")).toBe("K7QM-4XPR");
    expect(formatClientCode("VfUeoDUNBXd03aq4LD73Bw")).toBe("VfUeoDUNBXd03aq4LD73Bw");
    expect(normaliseClientCode(" k7qm-4xpr ")).toBe("K7QM4XPR");
  });

  it("opens the client's upload page for a code they type", async () => {
    renderAt("/client");
    expect(screen.getByRole("heading", { level: 1, name: "Enter your code" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Enter your code"), { target: { value: "jd7k-4q" } });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Continue" })));
    expect(screen.getByRole("heading", { level: 1, name: "Send your letter" })).toBeTruthy();
  });

  it("says so when a code is not found", async () => {
    renderAt("/client");
    fireEvent.change(screen.getByLabelText("Enter your code"), { target: { value: "ZZZZ-ZZZZ" } });
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Continue" })));
    expect(screen.getByRole("alert").textContent).toContain("We could not find that code");
  });
});

describe("view shortcuts", () => {
  it("opens from the (?) in the header and links to every view", () => {
    renderAt("/provider");
    const button = screen.getByRole("button", { name: /switch between the client, solicitor and caseworker views/ });
    expect(button.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    for (const name of ["Client", "Solicitor", "LAA caseworker", "All three side by side"]) {
      expect(screen.getByRole("link", { name })).toBeTruthy();
    }
    expect(screen.getByRole("link", { name: "Solicitor" }).getAttribute("aria-current")).toBe("page");
  });

  it("closes on Escape", () => {
    renderAt("/caseworker");
    const button = screen.getByRole("button", { name: /switch between/ });
    fireEvent.click(button);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
  });

  it("replaces the old black view switcher", () => {
    renderAt("/provider");
    expect(screen.queryByRole("navigation", { name: "View switcher" })).toBeNull();
  });
});

describe("client upload fits the device", () => {
  it("offers the camera on a phone", () => {
    stubScreen(true);
    renderAt("/client/jd7k4q");
    expect(screen.getByText("Take photos")).toBeTruthy();
    expect(screen.queryByText("Drag your letter here")).toBeNull();
  });

  it("offers drag and drop and a file button on a computer", () => {
    stubScreen(false);
    renderAt("/client/jd7k4q");
    expect(screen.getByText("Drag your letter here")).toBeTruthy();
    expect(screen.getByText("Choose a file")).toBeTruthy();
    expect(screen.queryByText("Take photos")).toBeNull();
    expect(screen.getByText(/Choose all the pages at once/)).toBeTruthy();
  });
});
