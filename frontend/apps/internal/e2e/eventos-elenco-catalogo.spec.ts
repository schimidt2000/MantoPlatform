import { expect, test } from "@playwright/test";

/**
 * Auto-vínculo de figurino ao escolher um Personagem do catálogo em Novo Evento (feature 185,
 * US4/FR-013): a linha de elenco nasce com o nome e a Ficha de Figurino já preenchidos.
 */
test.describe("Novo Evento — escolher personagem do catálogo", () => {
  let itemId: number | null = null;
  let figurinoId: number | null = null;

  test.beforeEach(async ({ request }) => {
    const figurinoResp = await request.post("/api/figurino", {
      data: { character_name: "Verify185 Figurino Playwright", pieces: [], tags: [] },
    });
    expect(figurinoResp.ok()).toBeTruthy();
    figurinoId = (await figurinoResp.json()).id;

    const itemResp = await request.post("/api/admin/catalogo", {
      multipart: {
        name: "Verify185 Tema Elenco Playwright",
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
    itemId = (await itemResp.json()).id;

    const characterResp = await request.post(`/api/admin/catalogo/${itemId}/personagens`, {
      multipart: {
        name: "Gatuno Playwright Elenco",
        video_url: "",
        figurino_sheet_id: String(figurinoId),
      },
    });
    expect(characterResp.ok()).toBeTruthy();
  });

  test.afterEach(async ({ request }) => {
    if (itemId) await request.delete(`/api/admin/catalogo/${itemId}`);
    if (figurinoId) await request.delete(`/api/figurino/${figurinoId}`);
    itemId = null;
    figurinoId = null;
  });

  test("escolher Personagem do catálogo pré-preenche nome e figurino no elenco", async ({ page }) => {
    await page.goto("/events/new");
    await expect(page.locator("#bloco-elenco")).toBeVisible();

    await page
      .getByLabel("Escolher do catálogo")
      .selectOption({ label: "Gatuno Playwright Elenco" });

    const names = page.getByLabel("Nome do personagem");
    await expect(names.last()).toHaveValue("Gatuno Playwright Elenco");

    const figurinoSelects = page.getByLabel("Buscar figurino");
    const selectedLabel = await figurinoSelects.last().evaluate((el: HTMLSelectElement) => {
      return el.options[el.selectedIndex]?.textContent ?? "";
    });
    expect(selectedLabel).toBe("Verify185 Figurino Playwright");
  });

  test("escolher o Tema completo (pacote) pré-preenche o nome sem figurino", async ({ page }) => {
    await page.goto("/events/new");
    await expect(page.locator("#bloco-elenco")).toBeVisible();

    await page
      .getByLabel("Escolher do catálogo")
      .selectOption({ label: "Verify185 Tema Elenco Playwright (pacote completo)" });

    const names = page.getByLabel("Nome do personagem");
    await expect(names.last()).toHaveValue("Verify185 Tema Elenco Playwright");
  });
});
