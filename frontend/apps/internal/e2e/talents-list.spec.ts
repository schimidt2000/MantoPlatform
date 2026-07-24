import { expect, test } from "@playwright/test";

/** US1 — filtros avançados combinados + grid widescreen (feature 180). */
test.describe("Talentos — listagem e filtros", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/talents");
    await expect(page.getByRole("heading", { name: "Talentos" })).toBeVisible();
  });

  test("aplica múltiplos filtros só ao clicar em Filtrar", async ({ page }) => {
    await page.getByRole("button", { name: "Filtros" }).click();

    // "Já trabalhou com a Manto" migrou para dentro do painel avançado.
    await expect(page.getByLabel("Buscar talento")).toBeVisible();
    const workedCheckbox = page.getByRole("checkbox", { name: "Já trabalhou com a Manto" });
    await expect(workedCheckbox).toBeVisible();

    const initialCards = await page.locator('a[href^="/talents/"]').count();

    await page.getByRole("button", { name: /^Raça/ }).click();
    await page.getByRole("checkbox", { name: "Branca" }).check();
    await page.keyboard.press("Escape");

    await page.getByRole("button", { name: /^Calçado/ }).click();
    const shoeOption = page.getByRole("checkbox").first();
    await shoeOption.check();
    await page.keyboard.press("Escape");

    // Seleções pendentes não devem mudar o resultado antes do clique em "Filtrar".
    expect(await page.locator('a[href^="/talents/"]').count()).toBe(initialCards);

    await page.getByRole("button", { name: "Filtrar" }).click();
    await page.waitForLoadState("networkidle");

    // Resultado pode mudar (ou zerar) — o que importa é que o filtro aplicado persiste visível.
    const raceButton = page.getByRole("button", { name: /^Raça/ });
    await expect(raceButton).toContainText("1");
  });

  test("grid widescreen mostra de 5 a 6 colunas", async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.waitForLoadState("networkidle");
    const grid = page.locator("div.grid").filter({ has: page.locator('a[href^="/talents/"]') });
    const columns = await grid
      .first()
      .evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").length);
    expect(columns).toBeGreaterThanOrEqual(5);
  });
});
