import { expect, test } from "@playwright/test";

/**
 * Gerenciador de Catálogo Interno (feature 185, US3): chip input de tags e painel de
 * Personagens filhos com vínculo de Ficha de Figurino.
 */
test.describe("Admin Catálogo — Temas e Personagens", () => {
  let createdItemId: string | null = null;

  test.afterEach(async ({ request }) => {
    if (createdItemId) {
      await request.delete(`/api/admin/catalogo/${createdItemId}`);
      createdItemId = null;
    }
  });

  test("cria um Tema com tags via chip input e video_url", async ({ page }) => {
    await page.goto("/admin/catalogo/novo");
    await expect(page.getByRole("heading", { name: "Novo produto" })).toBeVisible();

    await page.getByLabel("Nome").fill("Verify185 Playwright Tema");

    const tagsInput = page.getByLabel("Tags");
    await tagsInput.fill("verificacao");
    await tagsInput.press("Enter");
    await expect(page.getByText("verificacao")).toBeVisible();

    await page.getByPlaceholder("https://...").fill("https://example.com/video.mp4");

    await page.setInputFiles('input[type="file"]', {
      name: "foto.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("fake-jpg-bytes"),
    });

    await page.getByRole("button", { name: "Criar produto" }).click();
    await expect(page).toHaveURL(/\/admin\/catalogo$/);
    await expect(page.getByText("Verify185 Playwright Tema")).toBeVisible();

    const editLink = page.getByRole("link", { name: /Verify185 Playwright Tema/ });
    await editLink.click();
    await expect(page).toHaveURL(/\/admin\/catalogo\/\d+\/editar/);
    const match = page.url().match(/\/admin\/catalogo\/(\d+)\/editar/);
    createdItemId = match?.[1] ?? null;
    expect(createdItemId).not.toBeNull();
  });

  test("adiciona um Personagem filho a um Tema existente", async ({ page, request }) => {
    const createResp = await request.post("/api/admin/catalogo", {
      multipart: {
        name: "Verify185 Playwright Tema Personagem",
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
    expect(createResp.ok()).toBeTruthy();
    const created = await createResp.json();
    createdItemId = String(created.id);

    await page.goto(`/admin/catalogo/${created.id}/editar`);
    await expect(page.getByRole("heading", { name: "Editar produto" })).toBeVisible();

    await page.getByRole("heading", { name: "Personagens" }).scrollIntoViewIfNeeded();
    await page.getByLabel("Nome do personagem").fill("Gatuno Playwright");
    await page.getByRole("button", { name: "+ Adicionar personagem" }).click();
    await expect(page.getByText("Gatuno Playwright")).toBeVisible();
  });
});
