import { expect, test } from "@playwright/test";

/** US2 — perfil em modo leitura limpo + US3 — alternância para modo edição (feature 180). */
test.describe("Talentos — perfil", () => {
  test("modo leitura não expõe nenhum controle de upload/edição", async ({ page }) => {
    await page.goto("/talents");
    await page.locator('a[href^="/talents/"]').first().click();
    await page.waitForURL(/\/talents\/\d+$/);

    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    // Nenhum input de arquivo nem textarea de anotações deve existir fora do modo edição.
    await expect(page.locator('input[type="file"]')).toHaveCount(0);
    await expect(page.locator("textarea")).toHaveCount(0);
    await expect(page.getByText("Eventos", { exact: true })).toBeVisible();
    await expect(page.getByText("Total Faturado", { exact: true })).toBeVisible();
    await expect(page.getByText("Avaliações e Notas")).toBeVisible();
  });

  test("/talents/:id/edit redireciona para o modo edição unificado", async ({ page }) => {
    await page.goto("/talents");
    const firstCard = page.locator('a[href^="/talents/"]').first();
    const href = await firstCard.getAttribute("href");
    const id = href?.match(/\/talents\/(\d+)/)?.[1];
    expect(id).toBeTruthy();

    await page.goto(`/talents/${id}/edit`);
    await expect(page).toHaveURL(new RegExp(`/talents/${id}\\?edit=1`));
  });

  test("alterna para modo edição, altera um campo fechado e salva (reversível)", async ({ page }) => {
    // Não criamos/removemos talento aqui: sem endpoint de criação para staff (só o cadastro
    // público, com muitos campos obrigatórios fora do escopo desta feature — ver research.md
    // §8). Em vez disso, editamos um campo de um talento real e devolvemos o valor original ao
    // final, para não deixar side effect em manto_local.
    await page.goto("/talents");
    await page.locator('a[href^="/talents/"]').first().click();
    await page.waitForURL(/\/talents\/\d+$/);

    const editButton = page.getByRole("button", { name: "Editar" });
    if (!(await editButton.isVisible())) {
      test.skip(true, "Usuário de teste sem permissão de edição em talentos");
    }
    await editButton.click();
    await expect(page).toHaveURL(/[?&]edit=1/);

    const shoeSelect = page.getByLabel("Calçado");
    const originalShoe = await shoeSelect.inputValue();
    const newShoe = originalShoe === "40" ? "41" : "40";
    await shoeSelect.selectOption(newShoe);

    await page.getByRole("button", { name: "Salvar" }).click();
    await expect(page).not.toHaveURL(/[?&]edit=1/);
    await expect(page.getByRole("button", { name: "Editar" })).toBeVisible();
    await expect(page.getByText(`Calçado ${newShoe}`)).toBeVisible();

    // Restaura o valor original.
    await page.getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Calçado").selectOption(originalShoe);
    await page.getByRole("button", { name: "Salvar" }).click();
    await expect(page).not.toHaveURL(/[?&]edit=1/);
  });
});
