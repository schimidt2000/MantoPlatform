import { expect, test } from "@playwright/test";

/** Reconstrução do formulário de Cadastro/Edição de Eventos (feature 184): os 7 blocos,
 * validação em tempo real com auto-scroll, criação válida e edição de um evento existente. */
test.describe("Eventos — formulário de cadastro/edição", () => {
  test("todos os 7 blocos aparecem em /events/new", async ({ page }) => {
    await page.goto("/events/new");
    await expect(page.getByRole("heading", { name: "Novo evento" })).toBeVisible();
    await expect(page.locator("#bloco-cliente")).toBeVisible();
    await expect(page.locator("#bloco-dados-evento")).toBeVisible();
    await expect(page.locator("#bloco-elenco")).toBeVisible();
    await expect(page.locator("#bloco-valores")).toBeVisible();
    await expect(page.locator("#bloco-pagamento")).toBeVisible();
    await expect(page.locator("#bloco-contrato")).toBeVisible();
    await expect(page.locator("#bloco-observacoes")).toBeVisible();
  });

  test("gera o título automaticamente a partir do elenco e do tipo", async ({ page }) => {
    await page.goto("/events/new");
    await page.getByLabel("Tipo").selectOption("SHOW");

    await page.getByRole("button", { name: "+ Adicionar personagem / equipe" }).click();
    await page.getByRole("button", { name: "+ Adicionar personagem / equipe" }).click();
    const names = page.getByLabel("Nome do personagem");
    await names.nth(0).fill("Mickey");
    await names.nth(1).fill("Minnie");

    await page.getByRole("button", { name: "Gerar título automaticamente" }).click();
    await expect(page.locator("#title")).toHaveValue("(SHOW) MICKEY + MINNIE");
  });

  test("calculadora de desconto atualiza em tempo real", async ({ page }) => {
    await page.goto("/events/new");
    const valores = page.locator("#bloco-valores");
    const moneyInputs = valores.locator('input[type="text"]');
    await moneyInputs.nth(0).fill("1000,00");
    await moneyInputs.nth(1).fill("800,00");
    await expect(valores.getByText("20.0% de desconto")).toBeVisible();
  });

  test("validação: submeter vazio mostra o banner e rola até o primeiro campo inválido", async ({
    page,
  }) => {
    await page.goto("/events/new");
    await page.getByRole("button", { name: "Adicionar à Agenda" }).click();

    // O banner aparece tanto no topo quanto no rodapé do formulário (FR-023) — confirma os dois.
    const banners = page.getByText(
      "Existem campos obrigatórios não preenchidos. Verifique os destaques em vermelho.",
    );
    await expect(banners).toHaveCount(2);
    await expect(banners.first()).toBeVisible();
    await expect(banners.last()).toBeVisible();
    await expect(page.locator("#title")).toBeFocused();
  });

  test("cria um evento válido com sucesso e depois exclui (limpeza)", async ({ page }) => {
    await page.goto("/events/new");

    await page.locator("#title").fill("V184 Playwright");
    await page.getByLabel("Data *").fill("2027-05-20");
    await page.getByLabel("Horário de início *").fill("10:00");
    await page.getByLabel("Horário de fim *").fill("12:00");

    const valores = page.locator("#bloco-valores");
    const moneyInputs = valores.locator('input[type="text"]');
    await moneyInputs.nth(0).fill("500,00");
    await moneyInputs.nth(1).fill("500,00");
    await page.getByLabel("Vendedor responsável *").selectOption({ index: 1 });
    await page.getByLabel("Data da venda *").fill("2027-05-01");

    await page.getByRole("button", { name: "Adicionar à Agenda" }).click();
    await page.waitForURL(/\/events\/\d+$/, { timeout: 15_000 });
    await expect(page.getByText("V184 Playwright")).toBeVisible();

    // Limpeza: exclui o evento criado (também remove do Google Agenda via _delete_event_flow).
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Excluir evento" }).click();
    await page.waitForURL(/\/agenda/, { timeout: 15_000 });
  });

  test("edita um evento existente pela tela unificada (reversível)", async ({ page }) => {
    // Não criamos um evento novo aqui — edita um evento real já existente em manto_local e
    // devolve o campo alterado ao valor original ao final, mesmo padrão de
    // talents-detail.spec.ts (evita side effect e uma segunda escrita real no Google Agenda).
    // Busca um evento real via a própria API da agenda (a visão de calendário não expõe uma
    // lista plana de links — varre alguns meses a partir de hoje até achar um evento comercial
    // de verdade). Eventos do tipo "ensaio" (satélites automáticos, sem vendedor/valor de venda)
    // ficam fora do escopo da edição em bloco (spec.md, Assumptions) — pular candidatos assim.
    await page.goto("/agenda");
    let id: number | undefined;
    const base = new Date();
    for (let offset = 0; offset < 6 && !id; offset++) {
      const d = new Date(base.getFullYear(), base.getMonth() + offset, 1);
      const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      const res = await page.request.get(`/api/agenda?ym=${ym}`);
      const body = await res.json();
      for (const ev of body.events ?? []) {
        if (ev.is_satellite) continue;
        const detail = await (await page.request.get(`/api/events/${ev.id}`)).json();
        const venda = detail.venda;
        if (
          !detail.event.is_ensaio &&
          venda?.seller_id &&
          venda.is_cortesia_permuta === false &&
          (venda.sale_value_gross ?? 0) > 0 &&
          (venda.sale_value ?? 0) > 0
        ) {
          id = ev.id;
          break;
        }
      }
    }
    expect(id).toBeTruthy();

    await page.goto(`/events/${id}`);
    await page.waitForLoadState("networkidle");
    const editButton = page.getByRole("link", { name: "Editar" });
    const hasEditButton = await editButton.isVisible().catch(() => false);
    if (!hasEditButton) {
      test.skip(true, "Usuário de teste sem permissão de edição em eventos");
    }
    await editButton.click();
    await page.waitForURL(new RegExp(`/events/${id}/edit`));

    const description = page.getByLabel("Descrição do evento");
    const original = await description.inputValue();
    await description.fill(`${original} [teste temporário]`);
    await page.getByRole("button", { name: "Salvar alterações" }).click();
    await page.waitForURL(new RegExp(`/events/${id}$`), { timeout: 15_000 });

    // Restaura a descrição original.
    await page.goto(`/events/${id}/edit`);
    await page.getByLabel("Descrição do evento").fill(original);
    await page.getByRole("button", { name: "Salvar alterações" }).click();
    await page.waitForURL(new RegExp(`/events/${id}$`), { timeout: 15_000 });
  });
});
