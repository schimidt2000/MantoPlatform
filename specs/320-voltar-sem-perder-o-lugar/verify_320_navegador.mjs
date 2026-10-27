// Cenários de navegador da feature 320 (chamado pelo verify_320.py — não rode sozinho sem as
// variáveis V320_*). Imprime o progresso no stderr e, na última linha do stdout, um JSON
// { "<n>": [ok, "texto"] } que o orquestrador lê.
//
// Por que um navegador de verdade: o que a 320 muda é histórico, rolagem e sobreposição — nada
// disso existe num test_client. O Playwright é o que já está em frontend/node_modules (feature 180).

import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(AQUI, "..", "..", "frontend", "package.json"));
const { chromium } = require("playwright");

const INTERNO = process.env.V320_INTERNO;
const PUBLICO = process.env.V320_PUBLICO;
const EMAIL = process.env.V320_EMAIL;
const SENHA = process.env.V320_SENHA;
const DADOS = JSON.parse(process.env.V320_DADOS || "{}");
const SO = (process.env.V320_SO || "").split(",").filter(Boolean);
const CONTRAPROVA = Boolean(process.env.V320_CONTRAPROVA);

const IPHONE = {
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
};
const DESKTOP = { viewport: { width: 1280, height: 800 } };
// Tempo para a lista voltar e a rolagem ser aplicada (o hook tenta por até 1,5 s).
const ESPERA_RESTAURAR = 2000;

const resultados = {};
const log = (...a) => process.stderr.write(`[320] ${a.join(" ")}\n`);
const quer = (n) => SO.length === 0 || SO.includes(String(n));

class Falha extends Error {}
function garante(cond, msg) {
  if (!cond) throw new Falha(msg);
}

async function cenario(n, nome, fn) {
  if (!quer(n)) return;
  log(`cenário ${n} — ${nome}`);
  try {
    await fn();
    resultados[n] = [true, nome];
  } catch (e) {
    const motivo = e instanceof Falha ? e.message : `erro: ${e.message.split("\n")[0]}`;
    resultados[n] = [false, `${nome}: ${motivo}`];
    log(`  FALHOU: ${motivo}`);
  }
}

// ── utilidades de página ─────────────────────────────────────────────────────────────────────
async function novoContexto(browser, perfil, { logado = true, appInstalado = false } = {}) {
  const ctx = await browser.newContext(perfil);
  if (appInstalado) {
    // O sinal que o iPhone dá quando o sistema abre pela Tela de Início.
    await ctx.addInitScript(() => {
      Object.defineProperty(Navigator.prototype, "standalone", { get: () => true, configurable: true });
    });
  }
  if (logado) {
    const r = await ctx.request.post(`${INTERNO}/api/auth/login`, {
      data: { email: EMAIL, password: SENHA },
    });
    garante(r.ok(), `login pela API devolveu ${r.status()}`);
  }
  return ctx;
}

const scrollY = (page) => page.evaluate(() => Math.round(window.scrollY));

/** Rola até o elemento ficar no meio da tela e devolve o scrollY resultante. */
async function rolarAte(page, locator) {
  await locator.evaluate((el) => el.scrollIntoView({ block: "center" }));
  await page.waitForTimeout(300);
  return scrollY(page);
}

/** O elemento está pelo menos em parte dentro da janela visível? */
async function visivelNaTela(locator) {
  if ((await locator.count()) === 0) return false;
  return locator.first().evaluate((el) => {
    const r = el.getBoundingClientRect();
    return r.bottom > 0 && r.top < window.innerHeight;
  });
}

// ── catálogo público ─────────────────────────────────────────────────────────────────────────
const CARDS_PUBLICO = "main .grid > div > a";
let categoriaEscolhida = null;

async function prepararCatalogo(page) {
  await page.goto(`${PUBLICO}/`);
  await page.getByText(/personage(m|ns) encontrad/).waitFor({ timeout: 20000 });
  await page.getByPlaceholder("Buscar por nome, tema, estilo…").fill("a");
  const chips = page.locator("button", { hasText: /\(\d+\)$/ });
  const total = await chips.count();
  for (let i = 0; i < total; i++) {
    const chip = chips.nth(i);
    const texto = (await chip.innerText()).trim();
    if (texto.startsWith("Todos")) continue;
    await chip.click();
    await page.waitForTimeout(150);
    if ((await page.locator(CARDS_PUBLICO).count()) >= 8) {
      categoriaEscolhida = texto.replace(/\s*\(\d+\)$/, "");
      break;
    }
  }
  garante(categoriaEscolhida, "nenhuma categoria com 8 temas para a busca 'a'");
  const cards = page.locator(CARDS_PUBLICO);
  const alvo = cards.nth(Math.min(7, (await cards.count()) - 1));
  const href = await alvo.getAttribute("href");
  const y = await rolarAte(page, alvo);
  garante(y > 300, `a lista não rolou (scrollY=${y})`);
  return { href, y };
}

async function conferirCatalogo(page, href) {
  await page.getByText(/personage(m|ns) encontrad/).waitFor({ timeout: 20000 });
  await page.waitForTimeout(ESPERA_RESTAURAR);
  const busca = await page.getByPlaceholder("Buscar por nome, tema, estilo…").inputValue();
  garante(busca === "a", `a busca voltou "${busca}" em vez de "a"`);
  const ativo = page.locator("button.bg-accent", { hasText: categoriaEscolhida });
  garante((await ativo.count()) > 0, `a categoria "${categoriaEscolhida}" não está selecionada`);
  garante(
    await visivelNaTela(page.locator(`${CARDS_PUBLICO}[href="${href}"]`)),
    `o tema aberto (${href}) não está na tela (scrollY=${await scrollY(page)})`,
  );
}

// ── gerenciador de catálogo ──────────────────────────────────────────────────────────────────
const CARDS_ADMIN = 'a[href^="/admin/catalogo/"][href$="/editar"]';

async function prepararGerenciador(page) {
  await page.goto(`${INTERNO}/admin/catalogo`);
  await page.getByRole("button", { name: /Cards/ }).click();
  await page.getByPlaceholder("Buscar por nome…").fill("a");
  const situacao = page.locator("select").filter({ has: page.locator('option[value="ativo"]') });
  await situacao.selectOption("ativo");
  const categoria = page.locator("select").filter({ hasText: "Todas as categorias" });
  await categoria.waitFor();
  const opcoes = await categoria.locator("option").evaluateAll((os) => os.map((o) => o.value).filter(Boolean));
  let escolhida = null;
  for (const valor of opcoes) {
    await categoria.selectOption(valor);
    await page.waitForTimeout(900);
    await page.locator('[aria-busy="true"]').waitFor({ state: "detached", timeout: 10000 }).catch(() => {});
    if ((await page.locator(CARDS_ADMIN).count()) >= 8) {
      escolhida = valor;
      break;
    }
  }
  garante(escolhida, "nenhuma categoria com 8 produtos ativos para a busca 'a'");
  const alvo = page.locator(CARDS_ADMIN).nth(7);
  const href = await alvo.getAttribute("href");
  const nome = (await alvo.innerText()).trim();
  const y = await rolarAte(page, alvo);
  garante(y > 200, `a lista não rolou (scrollY=${y})`);
  return { href, nome, categoria: escolhida };
}

async function conferirGerenciador(page, { href, categoria }) {
  await page.locator(CARDS_ADMIN).first().waitFor({ timeout: 20000 });
  await page.waitForTimeout(ESPERA_RESTAURAR);
  const busca = await page.getByPlaceholder("Buscar por nome…").inputValue();
  garante(busca === "a", `a busca voltou "${busca}"`);
  const sel = page.locator("select").filter({ has: page.locator('option[value="ativo"]') });
  garante((await sel.inputValue()) === "ativo", "a situação voltou diferente de Ativos");
  const cat = page.locator("select").filter({ hasText: "Todas as categorias" });
  garante((await cat.inputValue()) === categoria, "a categoria não voltou");
  garante(
    await visivelNaTela(page.locator(`${CARDS_ADMIN}[href="${href}"]`)),
    `o produto aberto não está na tela (scrollY=${await scrollY(page)})`,
  );
}

// ── banco de talentos ────────────────────────────────────────────────────────────────────────
const CARDS_TALENTO = 'a[href^="/talents/"]';

async function prepararTalentos(page) {
  await page.goto(`${INTERNO}/talents`);
  await page.locator(CARDS_TALENTO).first().waitFor({ timeout: 20000 });
  await page.getByLabel("Buscar talento").fill("a");
  await page.getByRole("button", { name: "Filtros" }).click();
  await page.getByLabel("Já trabalhou com a Manto").check();
  await page.getByRole("button", { name: "Filtrar" }).click();
  await page.waitForTimeout(1200);
  const proxima = page.getByRole("button", { name: "Próxima ›" });
  let pagina = 1;
  if ((await proxima.count()) > 0 && (await proxima.isEnabled())) {
    await proxima.click();
    await page.getByText(/Página 2 de/).waitFor({ timeout: 15000 });
    pagina = 2;
  }
  const cards = page.locator(CARDS_TALENTO);
  const n = await cards.count();
  garante(n >= 8, `poucos talentos na tela (${n})`);
  const alvo = cards.nth(Math.min(n - 1, Math.floor(n * 0.7)));
  const href = await alvo.getAttribute("href");
  const y = await rolarAte(page, alvo);
  garante(y > 300, `a lista não rolou (scrollY=${y})`);
  return { href, pagina };
}

async function conferirTalentos(page, { href, pagina }) {
  await page.locator(CARDS_TALENTO).first().waitFor({ timeout: 20000 });
  await page.waitForTimeout(ESPERA_RESTAURAR);
  const busca = await page.getByLabel("Buscar talento").inputValue();
  garante(busca === "a", `a busca voltou "${busca}"`);
  if (pagina === 2) garante((await page.getByText(/Página 2 de/).count()) > 0, "não voltou na página 2");
  const filtro = page.getByLabel("Já trabalhou com a Manto");
  garante((await filtro.count()) > 0 && (await filtro.isChecked()), "o filtro 'Já trabalhou' não voltou");
  garante(
    await visivelNaTela(page.locator(`${CARDS_TALENTO}[href="${href}"]`)),
    `o talento aberto não está na tela (scrollY=${await scrollY(page)})`,
  );
}

// ── visualizador de arquivo ──────────────────────────────────────────────────────────────────
const VISUALIZADOR = "[data-visualizador-arquivo]";

async function linkDeComprovante(page, caminhos) {
  for (const caminho of caminhos) {
    const link = page.locator(`a[href$="${caminho}"]`).first();
    if ((await link.count()) === 0) continue;
    const r = await page.request.get(`${INTERNO}/uploads/${caminho}`);
    if (r.ok()) return link;
  }
  return null;
}

async function abrirNoVisualizador(page, ctx, link) {
  const paginasAntes = ctx.pages().length;
  const y = await rolarAte(page, link);
  await link.click();
  await page.waitForTimeout(1500);
  for (const p of ctx.pages()) if (p !== page) await p.close();
  garante(ctx.pages().length === paginasAntes && ctx.pages()[0] === page, "o arquivo abriu em outra aba/janela");
  garante(new URL(page.url()).pathname === "/gastos", `a página mudou para ${page.url()}`);
  const viz = page.locator(VISUALIZADOR);
  garante(await viz.isVisible().catch(() => false), "o visualizador não abriu");
  garante(await viz.getByRole("button", { name: "Voltar" }).isVisible(), "o botão Voltar não está visível");
  return y;
}

async function conferirFechado(page, y) {
  await page.waitForTimeout(800);
  garante((await page.locator(VISUALIZADOR).count()) === 0, "o visualizador não fechou");
  garante(new URL(page.url()).pathname === "/gastos", `a página mudou para ${page.url()}`);
  const agora = await scrollY(page);
  garante(Math.abs(agora - y) <= 10, `a rolagem mudou (${y} → ${agora})`);
}

// ── execução ─────────────────────────────────────────────────────────────────────────────────
const browser = await chromium.launch();
try {
  // Catálogo público no celular — é onde a comercial usa durante o atendimento.
  if (quer(1) || quer(2) || quer(3)) {
    const ctx = await novoContexto(browser, IPHONE, { logado: false });
    const page = await ctx.newPage();
    await cenario(1, "catálogo público: '← Voltar ao catálogo' devolve busca, categoria e rolagem", async () => {
      const { href } = await prepararCatalogo(page);
      await page.locator(`${CARDS_PUBLICO}[href="${href}"]`).click();
      await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
      await page.getByText("← Voltar ao catálogo").first().click();
      await page.waitForURL((u) => u.pathname === "/", { timeout: 15000 });
      await conferirCatalogo(page, href);
    });
    await cenario(2, "catálogo público: voltar do navegador devolve busca, categoria e rolagem", async () => {
      const { href } = await prepararCatalogo(page);
      await page.locator(`${CARDS_PUBLICO}[href="${href}"]`).click();
      await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
      await page.goBack();
      await conferirCatalogo(page, href);
    });
    await cenario(3, "catálogo público: endereço com busca e categoria abre filtrado", async () => {
      if (!categoriaEscolhida) await prepararCatalogo(page);
      const p2 = await ctx.newPage();
      await p2.goto(`${PUBLICO}/?q=a&categoria=${encodeURIComponent(categoriaEscolhida)}`);
      await p2.getByText(/personage(m|ns) encontrad/).waitFor({ timeout: 20000 });
      garante((await p2.getByPlaceholder("Buscar por nome, tema, estilo…").inputValue()) === "a", "a busca não veio do endereço");
      garante((await p2.locator("button.bg-accent", { hasText: categoriaEscolhida }).count()) > 0, "a categoria não veio do endereço");
      await p2.close();
    });
    await ctx.close();
  }

  if (quer(4) || quer(5) || quer(6) || quer(11)) {
    const ctx = await novoContexto(browser, DESKTOP);
    const page = await ctx.newPage();
    await cenario(4, "gerenciador: voltar do card e do menu 'Editar' devolve filtros e rolagem", async () => {
      const info = await prepararGerenciador(page);
      await page.locator(`${CARDS_ADMIN}[href="${info.href}"]`).click();
      await page.waitForURL((u) => u.pathname === info.href, { timeout: 15000 });
      await page.getByRole("link", { name: "‹ Catálogo" }).click();
      await page.waitForURL((u) => u.pathname === "/admin/catalogo", { timeout: 15000 });
      await conferirGerenciador(page, info);
      // Agora pelo menu do card + voltar do navegador.
      await page.getByRole("button", { name: `Mais ações para ${info.nome}` }).click();
      await page.getByRole("menuitem", { name: "Editar" }).click();
      await page.waitForURL((u) => u.pathname === info.href, { timeout: 15000 });
      await page.goBack();
      await conferirGerenciador(page, info);
    });
    await cenario(5, "talentos: voltar da ficha devolve busca, filtro, página e rolagem", async () => {
      const info = await prepararTalentos(page);
      await page.locator(`${CARDS_TALENTO}[href="${info.href}"]`).click();
      await page.waitForURL((u) => u.pathname === info.href, { timeout: 15000 });
      await page.getByRole("link", { name: /Talentos ativos/ }).click();
      await page.waitForURL((u) => u.pathname === "/talents", { timeout: 15000 });
      await conferirTalentos(page, info);
      await page.locator(`${CARDS_TALENTO}[href="${info.href}"]`).click();
      await page.waitForURL((u) => u.pathname === info.href, { timeout: 15000 });
      await page.goBack();
      await conferirTalentos(page, info);
    });
    await cenario(6, "talentos: /talents?status=pending abre em Pendentes", async () => {
      await page.goto(`${INTERNO}/talents?status=pending`);
      const botao = page.getByRole("button", { name: /^Pendentes/ });
      await botao.waitFor({ timeout: 15000 });
      await page.waitForTimeout(500);
      garante((await botao.getAttribute("class")).includes("bg-accent"), "abriu em Ativos");
    });
    await cenario(11, "navegação nova pelo menu começa do topo", async () => {
      await page.goto(`${INTERNO}/talents`);
      await page.locator(CARDS_TALENTO).first().waitFor({ timeout: 20000 });
      await page.evaluate(() => window.scrollTo(0, 1500));
      await page.waitForTimeout(300);
      await page.getByRole("link", { name: "Gastos Extras" }).first().click();
      await page.waitForURL((u) => u.pathname === "/gastos", { timeout: 15000 });
      await page.waitForTimeout(800);
      garante((await scrollY(page)) === 0, `a tela nova abriu rolada (scrollY=${await scrollY(page)})`);
      await page.evaluate(() => window.scrollTo(0, 600));
      await page.getByRole("link", { name: "Banco de Talentos" }).first().click();
      await page.waitForURL((u) => u.pathname === "/talents", { timeout: 15000 });
      await page.locator(CARDS_TALENTO).first().waitFor({ timeout: 20000 });
      await page.waitForTimeout(ESPERA_RESTAURAR);
      garante((await scrollY(page)) === 0, `a lista aberta pelo menu não começou do topo (scrollY=${await scrollY(page)})`);
    });
    await ctx.close();
  }

  if (quer(7) || quer(8)) {
    const ctx = await novoContexto(browser, IPHONE, { appInstalado: true });
    const page = await ctx.newPage();
    await page.goto(`${INTERNO}/gastos`);
    await page.locator("table").first().waitFor({ timeout: 20000 });
    const foto = await linkDeComprovante(page, DADOS.comprovantes?.fotos ?? []);
    const pdf = await linkDeComprovante(page, DADOS.comprovantes?.pdfs ?? []);
    let yFoto = null;
    let yPdf = null;
    await cenario(7, "gastos (iPhone): comprovante em foto e em PDF abre dentro do sistema", async () => {
      garante(foto && pdf, "não há comprovante em foto e em PDF com arquivo local");
      yFoto = await abrirNoVisualizador(page, ctx, foto);
      const img = page.locator(`${VISUALIZADOR} img`);
      await img.waitFor({ timeout: 10000 });
      garante(await img.evaluate((el) => el.complete && el.naturalWidth > 0), "a foto não carregou");
      await page.locator(VISUALIZADOR).getByRole("button", { name: "Voltar" }).click();
      await page.waitForTimeout(800);
      yPdf = await abrirNoVisualizador(page, ctx, pdf);
      const canvas = page.locator(`${VISUALIZADOR} canvas`).first();
      await canvas.waitFor({ timeout: 20000 });
      await page.waitForTimeout(1500);
      const desenhado = await canvas.evaluate((c) => {
        if (!c.width || !c.height) return false;
        const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
        for (let i = 0; i < d.length; i += 4 * 97) if (d[i] < 240 || d[i + 1] < 240 || d[i + 2] < 240) return true;
        return false;
      });
      garante(desenhado, "a página do PDF não foi desenhada");
      garante(await page.getByRole("button", { name: "Baixar" }).isVisible(), "sem botão Baixar");
    });
    await cenario(8, "visualizador: 'Voltar' e voltar do navegador fecham no mesmo ponto", async () => {
      garante(foto && pdf && yPdf !== null, "depende do cenário 7");
      // O PDF do cenário 7 ainda está aberto: fecha pelo voltar do navegador.
      await page.goBack();
      await conferirFechado(page, yPdf);
      yFoto = await abrirNoVisualizador(page, ctx, foto);
      await page.locator(VISUALIZADOR).getByRole("button", { name: "Voltar" }).click();
      await conferirFechado(page, yFoto);
    });
    await ctx.close();
  }

  await cenario(10, "app instalado: menu 'Catálogo' na mesma janela e '← Voltar ao sistema'", async () => {
    const ctx = await novoContexto(browser, DESKTOP, { appInstalado: true });
    const page = await ctx.newPage();
    await page.goto(`${INTERNO}/gastos`);
    const item = page.locator('a[href="/catalogo/"]').first();
    await item.waitFor({ state: "attached", timeout: 15000 });
    garante((await item.getAttribute("target")) === null, "o item 'Catálogo' ainda abre em outra aba");
    // Em dev o catálogo é outro servidor; a navegação na mesma janela é simulada indo direto.
    await page.goto(`${PUBLICO}/`);
    const voltar = page.getByRole("button", { name: /Voltar ao sistema/ });
    await voltar.waitFor({ timeout: 15000 });
    await voltar.click();
    await page.waitForURL((u) => u.href.startsWith(INTERNO) && u.pathname === "/gastos", { timeout: 15000 });
    await ctx.close();
    const comum = await novoContexto(browser, IPHONE, { logado: false });
    const p2 = await comum.newPage();
    await p2.goto(`${PUBLICO}/`);
    await p2.getByText(/personage(m|ns) encontrad/).waitFor({ timeout: 20000 });
    garante((await p2.getByRole("button", { name: /Voltar ao sistema/ }).count()) === 0, "a cliente vê 'Voltar ao sistema'");
    await comum.close();
  });
} finally {
  await browser.close();
}

if (CONTRAPROVA) log("(contraprova: os cenários acima TÊM de falhar)");
process.stdout.write(`${JSON.stringify(resultados)}\n`);
