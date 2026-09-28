import { expect, test } from "@playwright/test";


test.beforeEach(async ({ page }) => {
  // O navegador roda em container; apenas o host é reescrito para alcançar a
  // API real publicada pelo Compose. Nenhuma resposta é simulada.
  await page.route("http://localhost:8001/**", async (route) => {
    await route.continue({
      url: route.request().url().replace("localhost", "host.docker.internal"),
    });
  });
});


test("registra, altera e limpa uma marcação usando a API real", async ({
  page,
  request,
}) => {
  const now = new Date();
  const targetDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-20`;
  await request.delete(
    `http://host.docker.internal:8001/api/attendance/${targetDate}?user_id=ana`,
    { headers: { "X-User": "ana" } },
  );
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /acompanhe sua presença/i }),
  ).toBeVisible();

  const targetDay = page.getByRole("gridcell", {
    name: /20 de .*sem marcação/i,
  });
  await targetDay.click();
  await page.locator('input[name="status"][value="present"]').check();
  await page
    .getByPlaceholder("Ex.: reunião com o time")
    .fill("Dia de integração E2E");
  await page.getByRole("button", { name: "Salvar marcação" }).click();
  await expect(page.getByRole("status")).toContainText("Marcação salva");

  await page.getByRole("gridcell", { name: /20 de .*fui ao polo/i }).click();
  await page.locator('input[name="status"][value="absent"]').check();
  await page.getByRole("button", { name: "Salvar marcação" }).click();
  await expect(page.getByRole("status")).toContainText("Marcação salva");

  await page.getByRole("gridcell", { name: /20 de .*não fui/i }).click();
  await page.getByRole("button", { name: "Limpar marcação" }).click();
  await expect(
    page.getByRole("gridcell", { name: /20 de .*sem marcação/i }),
  ).toBeVisible();
});


test("navega, troca perfil e consulta a visão real do time", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Próximo mês" }).click();
  await page.getByRole("button", { name: "Mês anterior" }).click();

  await page.getByLabel("Perfil fictício").selectOption("bruno");
  await expect(page.getByText("Olá, Bruno")).toBeVisible();
  await page.getByLabel("Perfil fictício").selectOption("ana");

  await page.getByRole("button", { name: /visão do time/i }).click();
  await expect(page.getByText("Bruno Demo")).toBeVisible();
  await expect(page.getByText("Carla Demo")).toBeVisible();
  await expect(page.getByText("Diego Demo")).toBeVisible();

  await page.getByRole("button", { name: /Bruno Demo/i }).click();
  await expect(
    page.getByRole("heading", { name: "Calendário de Bruno Demo" }),
  ).toBeVisible();
});
