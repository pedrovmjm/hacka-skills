import { expect, test } from "@playwright/test";


async function connectLiveApi(page) {
  await page.route("http://localhost:8001/**", async (route) => {
    const target = route.request().url().replace(
      "http://localhost:8001",
      "http://host.docker.internal:8001",
    );
    await route.continue({ url: target });
  });
}


test("completes the visit lifecycle in the browser", async ({ page }) => {
  await connectLiveApi(page);

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Planeje suas idas/i })).toBeVisible();
  await expect(page.getByText("Aula presencial")).toBeVisible();

  const profile = page.getByLabel("Perfil de demonstracao");
  await profile.selectOption("bruno");
  await expect(page.getByText("Atendimento academico")).toBeVisible();
  await profile.selectOption("ana");
  await expect(page.getByText("Aula presencial")).toBeVisible();

  const cancelledBefore = Number(
    await page.locator(".summary article").filter({ hasText: "Canceladas" }).locator("strong").textContent(),
  );
  const marker = Date.now().toString();
  const purpose = `Validacao navegador ${marker}`;
  const updatedPurpose = `${purpose} atualizada`;

  await page.getByLabel("Nome do visitante").fill("Ana E2E");
  await page.getByLabel("Data").fill("2026-12-10");
  await page.getByLabel("Horario").fill("16:20");
  await page.getByLabel("Finalidade").fill(purpose);
  await page.getByLabel("Acompanhantes").fill("1");
  await page.getByLabel("Observacoes").fill("Criada pelo fluxo automatizado");
  await page.getByRole("button", { name: "Agendar ida" }).click();
  await expect(page.getByRole("status")).toContainText("Ida agendada");

  let card = page.locator(".visit-card").filter({ hasText: purpose });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Alterar" }).click();
  await page.getByLabel("Data").fill("2026-12-11");
  await page.getByLabel("Finalidade").fill(updatedPurpose);
  await page.getByRole("button", { name: "Salvar alteracoes" }).click();
  await expect(page.getByRole("status")).toContainText("Agendamento atualizado");

  card = page.locator(".visit-card").filter({ hasText: updatedPurpose });
  await expect(card).toContainText("2026-12-11");
  page.once("dialog", (dialog) => dialog.accept());
  await card.getByRole("button", { name: "Cancelar" }).click();
  await expect(page.getByRole("status")).toContainText("Agendamento cancelado");
  await expect(page.locator(".visit-card").filter({ hasText: updatedPurpose })).toContainText("Cancelada");
  await expect(
    page.locator(".summary article").filter({ hasText: "Canceladas" }).locator("strong"),
  ).toHaveText(String(cancelledBefore + 1));
});


test("renders persisted notes in the browser", async ({ page }) => {
  await connectLiveApi(page);
  await page.goto("/");
  await expect(page.getByText("Aula presencial")).toBeVisible();

  const marker = Date.now().toString();
  const note = `<img src="missing-${marker}" onerror="document.body.dataset.noteCheck='${marker}'">`;
  await page.getByLabel("Nome do visitante").fill("Ana E2E");
  await page.getByLabel("Data").fill("2026-12-20");
  await page.getByLabel("Horario").fill("10:10");
  await page.getByLabel("Finalidade").fill(`Nota persistida ${marker}`);
  await page.getByLabel("Observacoes").fill(note);
  await page.getByRole("button", { name: "Agendar ida" }).click();

  await expect(page.getByRole("status")).toContainText("Ida agendada");
  await expect(page.locator("body")).toHaveAttribute("data-note-check", marker);
});
