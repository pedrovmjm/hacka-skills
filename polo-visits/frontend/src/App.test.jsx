import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";


const visits = [
  {
    id: 1,
    user_id: "ana",
    visitor_name: "Ana Demo",
    visit_date: "2026-10-05",
    start_time: "09:00",
    purpose: "Aula presencial",
    notes: "<img src=x onerror=alert(1)>",
    companions: 0,
    status: "scheduled",
  },
];

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (url) => ({
      ok: true,
      json: async () => String(url).includes("summary")
        ? { scheduled: 1, completed: 0, cancelled: 0, total: 1 }
        : visits,
    })));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("renders the scheduling dashboard", async () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /Planeje suas idas/i })).toBeInTheDocument();
    expect(await screen.findByText("Aula presencial")).toBeInTheDocument();
    expect(screen.getByText("Agendadas").nextSibling).toHaveTextContent("1");
  });

  it("renders notes supplied by the API", async () => {
    const { container } = render(<App />);
    await waitFor(() => expect(container.querySelector(".notes img")).not.toBeNull());
    expect(container.querySelector(".notes img").getAttribute("onerror")).toBe("alert(1)");
  });
});

