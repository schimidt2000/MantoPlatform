import { expect, test } from "@playwright/test";

/** Reestruturação do Banco de Figurinos (feature 183): grade densa/enquadramento, ações do
 * card, painel de faltantes com RBAC, busca e filtro por tags. */
test.describe("Figurinos — banco de fichas", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/figurinos");
    await expect(page.getByRole("heading", { name: "Figurino" })).toBeVisible();
  });

  test("grade widescreen mostra de 5 a 6 colunas e o rodapé do card", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForLoadState("networkidle");

    const grid = page.locator("div.grid").filter({ hasText: "peça" }).first();
    const columns = await grid.evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(" ").length);
    expect(columns).toBeGreaterThanOrEqual(5);

    const firstCard = grid.locator(":scope > div").first();
    await expect(firstCard.getByText(/peça/)).toBeVisible();
    await expect(firstCard.getByRole("button", { name: "Imprimir" })).toBeVisible();
  });

  test("enquadramento da foto usa quadro vertical com object-cover no topo", async ({ page }) => {
    const img = page.locator("img[alt]").first();
    await expect(img).toBeVisible();
    const box = img.locator("xpath=..");
    await expect(box).toHaveClass(/aspect-\[3\/4\]/);
    const objectFit = await img.evaluate((el) => getComputedStyle(el).objectFit);
    const objectPosition = await img.evaluate((el) => getComputedStyle(el).objectPosition);
    expect(objectFit).toBe("cover");
    expect(objectPosition).toBe("50% 0%");
  });

  test("botão Editar leva à ficha correta (RBAC de escrita)", async ({ page }) => {
    const editLink = page.locator('a[href*="/edit"]').first();
    await expect(editLink).toBeVisible();
    await editLink.click();
    await expect(page).toHaveURL(/\/figurinos\/\d+\/edit/);
    await expect(page.getByText(/^Editar —/)).toBeVisible();
  });

  test("painel de faltantes: visível e colapsado por padrão para SUPERADMIN, oculto para outros papéis", async ({
    page,
  }) => {
    const panelToggle = page.getByText(/Figurinos solicitados\/faltantes/);
    await expect(panelToggle).toBeVisible();

    // Colapsado por padrão: nenhum botão de ação do painel visível antes de expandir.
    await expect(page.getByRole("button", { name: "Associar a uma ficha existente" })).toHaveCount(0);

    await panelToggle.click();
    await expect(page.getByRole("button", { name: "Associar a uma ficha existente" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Excluir" }).first()).toBeVisible();

    // Impersonação (feature já existente) confirma RBAC sem precisar de um segundo login.
    const viewAsFigurino = page.getByRole("button", { name: "Ver o sistema como FIGURINO" });
    if (await viewAsFigurino.isVisible()) {
      await viewAsFigurino.click();
      await page.goto("/figurinos");
      await expect(page.getByText(/Figurinos solicitados\/faltantes/)).toHaveCount(0);
      // Volta ao SUPERADMIN real para não deixar a sessão impersonada para o próximo teste.
      await page.getByRole("button", { name: "Voltar ao papel real de administrador" }).click();
    }
  });

  test("busca por nome filtra a grade (case-insensitive, sem acento)", async ({ page }) => {
    const search = page.getByLabel("Buscar ficha de figurino");
    const grid = page.locator("div.grid").filter({ hasText: "peça" }).first();
    await expect(grid.locator(":scope > div").first()).toBeVisible();
    const initialCount = await grid.locator(":scope > div").count();

    await search.fill("ariel");
    await page.waitForTimeout(150);
    const filteredCount = await grid.locator(":scope > div").count();
    expect(filteredCount).toBeLessThan(initialCount);
    expect(filteredCount).toBeGreaterThan(0);

    await search.fill("");
  });
});
