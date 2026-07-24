import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type APIRequestContext } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Feature 182 — Revisão de Mídia estilo Vimeo. Cobre as 4 user stories da spec:
 * US1 (player), US2 (comentários por timestamp), US3 (layout 2 colunas), US4 (versões+status).
 *
 * Setup via a própria API do app (não manipulação direta de banco) — cria um espaço de
 * revisão real com o vídeo de fixture, e remove tudo ao final (`afterAll`). Os testes rodam
 * em sequência (mesma premissa de `playwright.config.ts`: `fullyParallel: false`, `workers: 1`)
 * porque compartilham o mesmo material entre passos (ex.: comentário criado na US2 é reusado
 * na verificação de versão da US4).
 *
 * Fora de escopo aqui (coberto por `specs/182-revisao-midia-vimeo/verify_182.py`): o 403 de
 * quem não tem `can_manage` tentando mudar o status — o harness e2e só autentica um usuário
 * (via `E2E_USER_EMAIL`/`E2E_USER_PASSWORD`), então a verificação de permissão negativa fica
 * no lado do backend.
 */

const FIXTURE_VIDEO = path.join(__dirname, "fixtures", "sample-review.webm");

let api: APIRequestContext;
let spaceId: number;
let assetId: number;

test.beforeAll(async ({ playwright, baseURL }) => {
  api = await playwright.request.newContext({ baseURL, storageState: "e2e/.auth/state.json" });
  const buffer = fs.readFileSync(FIXTURE_VIDEO);
  const createResp = await api.post("/api/revisao", {
    multipart: {
      title: "E2E — Revisão de Mídia estilo Vimeo",
      description: "",
      files: { name: "sample-review.webm", mimeType: "video/webm", buffer },
    },
  });
  expect(createResp.ok(), await createResp.text()).toBeTruthy();
  const created = await createResp.json();
  spaceId = created.id;

  const detailResp = await api.get(`/api/revisao/${spaceId}`);
  const detail = await detailResp.json();
  assetId = detail.assets[0].id;
});

test.afterAll(async () => {
  if (spaceId) await api.delete(`/api/revisao/${spaceId}`);
  await api.dispose();
});

test.describe("Revisão de Mídia — asset de vídeo", () => {
  test("US1 — play/pause, seek, velocidade e tempo formatado", async ({ page }) => {
    await page.goto(`/revisao/${spaceId}/asset/${assetId}`);
    const video = page.locator("video");
    await expect(video).toBeVisible();
    await expect(page.getByText(/^0:00 \/ 0:0\d$/)).toBeVisible({ timeout: 10_000 });

    // Foco neutro (fora de qualquer input) antes de testar atalhos.
    await page.getByRole("heading", { level: 1 }).click();

    const playButton = page.getByRole("button", { name: "Reproduzir" });
    await expect(playButton).toBeVisible();
    await page.keyboard.press("Space");
    await expect(page.getByRole("button", { name: "Pausar" })).toBeVisible();
    await page.keyboard.press("Space");
    await expect(page.getByRole("button", { name: "Reproduzir" })).toBeVisible();

    // Seta direita avança ~5s (vídeo de 6s — clampa perto do fim).
    await page.keyboard.press("ArrowRight");
    await expect(async () => {
      const t = await video.evaluate((el: HTMLVideoElement) => el.currentTime);
      expect(t).toBeGreaterThan(3);
    }).toPass({ timeout: 5_000 });

    // Velocidade: clicar em "1.5x" muda playbackRate do elemento nativo.
    await page.getByRole("button", { name: "1.5x" }).click();
    await expect(async () => {
      const rate = await video.evaluate((el: HTMLVideoElement) => el.playbackRate);
      expect(rate).toBe(1.5);
    }).toPass({ timeout: 5_000 });
  });

  test("US1 — atalhos de teclado são ignorados com foco em campo de texto", async ({ page }) => {
    await page.goto(`/revisao/${spaceId}/asset/${assetId}`);
    const video = page.locator("video");
    await expect(video).toBeVisible();

    const textarea = page.getByPlaceholder("Escreva um comentário…");
    await textarea.click();
    const before = await video.evaluate((el: HTMLVideoElement) => el.currentTime);
    await page.keyboard.press("Space");
    await page.keyboard.press("ArrowRight");
    const after = await video.evaluate((el: HTMLVideoElement) => el.currentTime);
    expect(after).toBe(before);
  });

  test("US2 — comentário captura timestamp, aparece no feed, seek e resolução", async ({ page }) => {
    await page.goto(`/revisao/${spaceId}/asset/${assetId}`);
    const video = page.locator("video");
    await expect(video).toBeVisible();

    // Avança um pouco para ter um timestamp != 0 pra capturar.
    await page.getByRole("heading", { level: 1 }).click();
    await page.keyboard.press("ArrowRight");
    await expect(async () => {
      const t = await video.evaluate((el: HTMLVideoElement) => el.currentTime);
      expect(t).toBeGreaterThan(2);
    }).toPass({ timeout: 5_000 });

    const textarea = page.getByPlaceholder("Escreva um comentário…");
    await textarea.click();
    await expect(page.getByText(/^@ \d:\d\d$/)).toBeVisible();

    const commentText = "Ajustar cor neste trecho";
    await textarea.fill(commentText);
    await page.getByRole("button", { name: "Comentar" }).click();
    await expect(page.getByText(commentText)).toBeVisible();

    // Marcador correspondente aparece na timeline.
    await expect(page.locator('[title^="Comentário em"]')).toHaveCount(1);

    // Clique no timestamp do comentário faz o player saltar.
    await video.evaluate((el: HTMLVideoElement) => {
      el.currentTime = 0;
    });
    const commentTimestampButton = page.locator("button", { hasText: /^@ \d:\d\d$/ }).last();
    await commentTimestampButton.click();
    await expect(async () => {
      const t = await video.evaluate((el: HTMLVideoElement) => el.currentTime);
      expect(t).toBeGreaterThan(1);
    }).toPass({ timeout: 5_000 });

    // Resolver e reabrir.
    await page.getByRole("button", { name: "Concluir" }).click();
    await expect(page.getByRole("button", { name: "Reabrir" })).toBeVisible();

    // Filtro "Apenas pendentes" esconde o comentário resolvido.
    await page.getByRole("button", { name: "Apenas pendentes" }).click();
    await expect(page.getByText("Nenhum comentário pendente.")).toBeVisible();
    await page.getByRole("button", { name: "Todos", exact: true }).click();
    await expect(page.getByText(commentText)).toBeVisible();

    // Reabre para deixar o estado limpo para o próximo teste.
    await page.getByRole("button", { name: "Reabrir" }).click();
    await expect(page.getByRole("button", { name: "Concluir" })).toBeVisible();
  });

  test("US3 — layout imersivo: 2 colunas em widescreen, empilhado em mobile", async ({ page }) => {
    await page.goto(`/revisao/${spaceId}/asset/${assetId}`);
    await expect(page.locator("video")).toBeVisible();
    const commentsHeading = page.getByRole("heading", { name: "Comentários" });

    await page.setViewportSize({ width: 1600, height: 900 });
    await expect(commentsHeading).toBeVisible();
    const videoBoxWide = await page.locator("video").boundingBox();
    const headingBoxWide = await commentsHeading.boundingBox();
    expect(videoBoxWide).not.toBeNull();
    expect(headingBoxWide).not.toBeNull();
    // Lado a lado: coluna direita começa à direita da esquerda, no topo da mesma "linha".
    expect(headingBoxWide!.x).toBeGreaterThan(videoBoxWide!.x + videoBoxWide!.width * 0.5);
    expect(headingBoxWide!.y).toBeLessThan(videoBoxWide!.y + videoBoxWide!.height);

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(commentsHeading).toBeVisible();
    const videoBoxMobile = await page.locator("video").boundingBox();
    const headingBoxMobile = await commentsHeading.boundingBox();
    expect(videoBoxMobile).not.toBeNull();
    expect(headingBoxMobile).not.toBeNull();
    // Empilhado: painel de comentários vem abaixo do player.
    expect(headingBoxMobile!.y).toBeGreaterThanOrEqual(videoBoxMobile!.y + videoBoxMobile!.height - 20);
  });

  test("US4 — seletor de versão e status de aprovação com um clique", async ({ page }) => {
    // Cria uma segunda versão via API (equivalente a "Enviar nova versão" na UI).
    const replaceResp = await api.post(`/api/revisao/asset/${assetId}/replace`, {
      multipart: {
        file: { name: "sample-review-v2.webm", mimeType: "video/webm", buffer: fs.readFileSync(FIXTURE_VIDEO) },
      },
    });
    expect(replaceResp.ok(), await replaceResp.text()).toBeTruthy();

    await page.goto(`/revisao/${spaceId}/asset/${assetId}`);
    await expect(page.getByText("v2 (atual)")).toBeVisible();
    await expect(page.getByText(/^v1/)).toBeVisible();

    // v2 (atual): status reseta para "Em Revisão" após o replace; nenhum comentário ainda.
    await expect(page.getByText("Em Revisão", { exact: true })).toBeVisible();

    // Trocar para v1 mostra o comentário criado na US2 e vira somente leitura.
    await page.getByText(/^v1/).click();
    await expect(page).toHaveURL(/[?&]v=1/);
    await expect(page.getByText("(somente leitura)")).toBeVisible();
    await expect(page.getByText("Ajustar cor neste trecho")).toBeVisible();

    // Volta para a versão atual e aprova com um clique.
    await page.getByText("v2 (atual)").click();
    await expect(page).not.toHaveURL(/[?&]v=/);
    await page.getByRole("button", { name: "Aprovado", exact: true }).click();
    await expect(page.getByText("Aprovado", { exact: true })).toBeVisible();

    // Persiste após reload.
    await page.reload();
    await expect(page.getByText("Aprovado", { exact: true })).toBeVisible();
  });
});
