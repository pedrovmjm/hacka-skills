import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const month = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}`;
const markedDate = `${month}-05`;
const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });

describe("App de presença", () => {
  beforeEach(() => {
    const attendance = { user_id: "ana", month, goal: 8, present_count: 3, remaining_count: 5, progress_percent: 37.5, days: [{ attendance_date: markedDate, status: "present", notes: "Planejamento" }] };
    vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
      const target = String(url);
      if (target.includes("team-attendance")) return response({ manager_id: "ana", month, goal: 8, team_size: 2, total_present: 9, average_present: 4.5, members: [{ user_id: "ana", name: "Ana Souza", present_count: 6, remaining_count: 2, progress_percent: 75, days: [{ attendance_date: markedDate, status: "present" }] }, { user_id: "bruno", name: "Bruno Lima", present_count: 3, remaining_count: 5, progress_percent: 37.5, days: [] }] });
      if (options.method === "PUT") return response(attendance);
      if (options.method === "DELETE") return { ok: true, status: 204, json: async () => null };
      return response(attendance);
    }));
  });
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it("exibe calendário, meta mensal e aviso demonstrativo", async () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /acompanhe sua presença/i })).toBeInTheDocument();
    expect(screen.getByText("Projeto demonstrativo, sem vínculo com o Itaú.")).toBeInTheDocument();
    expect(await screen.findByRole("grid", { name: /calendário/i })).toBeInTheDocument();
    expect(document.querySelector(".goal strong")).toHaveTextContent("3");
    expect(screen.getByText("de 8 dias")).toBeInTheDocument();
  });

  it("abre o editor e salva uma presença pelo contrato da API", async () => {
    render(<App />);
    const calendar = await screen.findByRole("grid");
    fireEvent.click(within(calendar).getByRole("gridcell", { name: new RegExp("5 de .*presença confirmada", "i") }));
    fireEvent.change(screen.getByPlaceholderText(/reunião com o time/i), { target: { value: "Encontro presencial" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar observação" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining(`/api/attendance/${markedDate}`), expect.objectContaining({ method: "PUT", headers: expect.objectContaining({ "X-User": "ana" }) })));
    expect(await screen.findByRole("status")).toHaveTextContent("Presença confirmada com sucesso");
  });

  it("caracteriza a injeção deliberada de HTML em observações persistidas", async () => {
    const payload = '<img src="x" data-testid="stored-xss" onerror="alert(1)">';
    fetch.mockResolvedValueOnce(response({ user_id: "ana", month, goal: 8, present_count: 1, remaining_count: 7, progress_percent: 12.5, days: [{ attendance_date: markedDate, status: "present", notes: payload }] }));
    const { container } = render(<App />);
    const calendar = await screen.findByRole("grid");
    fireEvent.click(within(calendar).getByRole("gridcell", { name: new RegExp("5 de .*presença confirmada", "i") }));
    const injectedImage = container.querySelector('.notes-preview img[data-testid="stored-xss"]');
    expect(injectedImage).not.toBeNull();
    expect(injectedImage.getAttribute("onerror")).toBe("alert(1)");
  });

  it("carrega a visão do time e abre o calendário de um integrante", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /visão do time/i }));
    expect(await screen.findByText("Ana Souza")).toBeInTheDocument();
    expect(screen.getByText("Total de presenças")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Ana Souza/i }));
    expect(screen.getByRole("heading", { name: "Calendário de Ana Souza" })).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining(`/api/team-attendance?manager_id=ana&month=${month}`), expect.objectContaining({ headers: { "X-User": "ana" } }));
  });

  it("exibe erro de carregamento de forma acessível", async () => {
    fetch.mockResolvedValueOnce(response({ detail: "Serviço indisponível" }, 503));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Serviço indisponível");
  });
});
