import { expect, test } from "@playwright/test";

/**
 * UX do Gerenciador de Catálogo + fluxo Ficha↔Catálogo↔Venda (feature 186): alternador
 * Cards/Árvore, kebab menu, seleção múltipla + ações em massa, vínculo bidirecional
 * Ficha↔Personagem com indicadores.
 */
test.describe("Gerenciador de Catálogo — UX (feature 186)", () => {
  let temaId: number | null = null;
  let figurinoId: number | null = null;
  let characterId: number | null = null;

  test.beforeEach(async ({ request }) => {
    const figurinoResp = await request.post("/api/figurino", {
      data: { character_name: "Verify186 Playwright Figurino", pieces: [], tags: [] },
    });
    expect(figurinoResp.ok()).toBeTruthy();
    figurinoId = (await figurinoResp.json()).id;

    const itemResp = await request.post("/api/admin/catalogo", {
      multipart: {
        name: "Verify186 Playwright Tema",
        description: "",
        tags: "",
        video_url: "",
        new_photos: {
          name: "foto.jpg",
          mimeType: "image/jpeg",
          buffer: Buffer.from("fake-jpg-bytes"),
        },
      },
    });
    expect(itemResp.ok()).toBeTruthy();
    temaId = (await itemResp.json()).id;

    const characterResp = await request.post(`/api/admin/catalogo/${temaId}/personagens`, {
      multipart: { name: "Verify186 Playwright Personagem", video_url: "" },
    });
    expect(characterResp.ok()).toBeTruthy();
    characterId = (await characterResp.json()).id;
  });

  test.afterEach(async ({ request }) => {
    if (temaId) await request.delete(`/api/admin/catalogo/${temaId}`);
    if (figurinoId) await request.delete(`/api/figurino/${figurinoId}`);
    temaId = null;
    figurinoId = null;
    characterId = null;
  });

  test("alterna para Árvore, expande o Tema e vê o indicador de figurino pendente", async ({ page }) => {
    await page.goto("/admin/catalogo");
    await page.getByRole("button", { name: "🌳 Árvore" }).click();

    const temaRow = page.getByText("Verify186 Playwright Tema");
    await expect(temaRow).toBeVisible();
    await temaRow.locator("xpath=ancestor::li[1]").getByLabel(/Expandir/).click();

    await expect(page.getByText("Verify186 Playwright Personagem")).toBeVisible();
    await expect(page.getByRole("button", { name: /Sem ficha — \+ Vincular/ })).toBeVisible();
  });

  test("vincular Ficha↔Personagem a partir da tela da Ficha é visível do lado do catálogo", async ({ page }) => {
    await page.goto(`/figurinos/${figurinoId}/edit`);
    await expect(page.getByText("Vincular a um Personagem do Catálogo")).toBeVisible();

    const autocomplete = page.getByPlaceholder("Buscar personagem do catálogo…");
    await autocomplete.fill("Verify186 Playwright Personagem");
    await page.getByRole("button", { name: "Verify186 Playwright Personagem" }).click();

    await expect(page.getByText("Verify186 Playwright Personagem — Verify186 Playwright Tema")).toBeVisible();

    // Confirma do lado do catálogo (painel de Personagens do Tema) — o badge verde, não a
    // <option> do <select> de busca de figurino (mesmo texto aparece nos dois lugares).
    await page.goto(`/admin/catalogo/${temaId}/editar`);
    await expect(page.locator("span.text-green")).toContainText("Verify186 Playwright Figurino");
  });

  test("seleção múltipla no modo Cards mostra a barra de ações em massa", async ({ page }) => {
    await page.goto("/admin/catalogo");
    await page.getByLabel("Selecionar Verify186 Playwright Tema").check();
    await expect(page.getByText("1 selecionado")).toBeVisible();
    await expect(page.getByRole("button", { name: "🚫 Inativar selecionados" })).toBeVisible();
    await expect(page.getByRole("button", { name: "📁 Mover para…" })).toHaveCount(0);

    await page.getByRole("button", { name: "Cancelar" }).click();
    await expect(page.getByText("1 selecionado")).toHaveCount(0);
  });

  test("mover Personagem em massa no modo Árvore realoca para outro Tema", async ({ page, request }) => {
    const otherItemResp = await request.post("/api/admin/catalogo", {
      multipart: {
        name: "Verify186 Playwright Tema Destino",
        description: "",
        tags: "",
        video_url: "",
        new_photos: { name: "d.jpg", mimeType: "image/jpeg", buffer: Buffer.from("fake-jpg-bytes") },
      },
    });
    const otherItemId = (await otherItemResp.json()).id;

    await page.goto("/admin/catalogo");
    await page.getByRole("button", { name: "🌳 Árvore" }).click();
    await page
      .getByText("Verify186 Playwright Tema", { exact: true })
      .locator("xpath=ancestor::li[1]")
      .getByLabel(/Expandir/)
      .click();

    await page.getByLabel("Selecionar Verify186 Playwright Personagem").check();
    await page.getByRole("button", { name: "📁 Mover para…" }).click();
    await page.getByLabel("Tema de destino").selectOption({ label: "Verify186 Playwright Tema Destino" });
    await page.getByRole("button", { name: "Confirmar" }).click();

    await expect(page.getByText("1 selecionado")).toHaveCount(0, { timeout: 10_000 });

    await request.delete(`/api/admin/catalogo/${otherItemId}`);
  });
});
