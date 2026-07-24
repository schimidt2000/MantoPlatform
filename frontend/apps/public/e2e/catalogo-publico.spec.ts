import { expect, test } from "@playwright/test";

/**
 * Catálogo Público (feature 185, US1/US2/US5): `noindex`, seção "Elenco Individual", vídeo em
 * autoplay mudo na galeria, e lista de interesse distinguindo Tema completo de Personagem
 * individual. Criação/remoção do Tema de teste via API (login staff), navegação como visitante
 * anônimo (o app público não usa sessão para nada além de criar o dado de teste).
 *
 * Requer `E2E_USER_EMAIL`/`E2E_USER_PASSWORD` (mesmo usuário SUPERADMIN/CASTING já usado pelos
 * specs de `apps/internal`) — mesma convenção do resto do repo, ver `e2e/global-setup.ts` lá.
 */
test.describe("Catálogo Público — Tema com Personagens e vídeo", () => {
  let temaId: number | null = null;
  let temaSlug: string | null = null;
  const characterName = "Gatuno Playwright Público";

  test.beforeEach(async ({ request }) => {
    const email = process.env.E2E_USER_EMAIL;
    const password = process.env.E2E_USER_PASSWORD;
    test.skip(!email || !password, "E2E_USER_EMAIL/E2E_USER_PASSWORD não configurados");

    const login = await request.post("/api/auth/login", { data: { email, password } });
    expect(login.ok()).toBeTruthy();

    const itemResp = await request.post("/api/admin/catalogo", {
      multipart: {
        name: "Verify185 Tema Público Playwright",
        description: "",
        tags: "",
        // URL real e estável (Google Cloud Storage) — necessário para exercitar o autoplay de
        // verdade sem cair no fallback silencioso de mídia quebrada (FR-017).
        video_url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        new_photos: {
          name: "foto.jpg",
          mimeType: "image/jpeg",
          buffer: Buffer.from("fake-jpg-bytes"),
        },
      },
    });
    expect(itemResp.ok()).toBeTruthy();
    const item = await itemResp.json();
    temaId = item.id;
    temaSlug = item.slug;

    const characterResp = await request.post(`/api/admin/catalogo/${temaId}/personagens`, {
      multipart: { name: characterName, video_url: "" },
    });
    expect(characterResp.ok()).toBeTruthy();
  });

  test.afterEach(async ({ request }) => {
    if (temaId) await request.delete(`/api/admin/catalogo/${temaId}`);
    temaId = null;
    temaSlug = null;
  });

  test("página do Tema tem noindex, elenco individual e vídeo em autoplay mudo", async ({ page }) => {
    await page.goto(`/${temaSlug}`);
    await expect(page.getByRole("heading", { name: "Verify185 Tema Público Playwright" })).toBeVisible();

    const robots = page.locator('meta[name="robots"]');
    await expect(robots).toHaveAttribute("content", "noindex, nofollow");

    await expect(page.getByRole("heading", { name: "Elenco Individual" })).toBeVisible();
    await expect(page.getByText(characterName)).toBeVisible();

    // A galeria mostra 1 mídia por vez (carrossel) — a foto (posição 0) vem antes do vídeo do
    // Tema (item adicional ao final); clica na 2ª miniatura para trocar para o vídeo.
    await page.locator("button.h-16.w-16").nth(1).click();

    const video = page.locator("video").first();
    await expect(video).toBeVisible();
    // Um único evaluate (autoplay/loop/muted juntos) evita round-trips separados que dariam
    // margem para o vídeo terminar de carregar/trocar de mídia entre uma checagem e outra.
    const state = await video.evaluate((el: HTMLVideoElement) => ({
      autoplay: el.autoplay,
      loop: el.loop,
      muted: el.muted,
      playsInline: el.playsInline,
    }));
    expect(state).toEqual({ autoplay: true, loop: true, muted: true, playsInline: true });
  });

  test("grade geral do catálogo também tem noindex", async ({ page }) => {
    await page.goto("/");
    const robots = page.locator('meta[name="robots"]');
    await expect(robots).toHaveAttribute("content", "noindex, nofollow");
  });

  test("adicionar Tema e Personagem à lista de interesse separadamente", async ({ page }) => {
    await page.goto(`/${temaSlug}`);

    await page.getByRole("button", { name: "Adicionar à lista" }).first().click();
    const characterCard = page.locator('[id^="personagem-"]', { hasText: characterName }).first();
    await characterCard.getByRole("button", { name: "Adicionar à lista" }).click();

    const stored = await page.evaluate(() =>
      JSON.parse(window.localStorage.getItem("manto_catalogo_wishlist") ?? "[]"),
    );
    expect(stored.length).toBe(2);
    expect(stored.some((i: { kind?: string }) => i.kind === "personagem")).toBe(true);
    expect(stored.some((i: { kind?: string }) => !i.kind || i.kind === "tema")).toBe(true);
  });
});
