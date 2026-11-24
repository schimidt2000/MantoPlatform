import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { Badge, Button, Foto, PageHeader, Skeleton, cn, useRestaurarRolagem } from "@manto/ui";
import {
  ROTULO_DA_SITUACAO,
  ROTULO_DO_TIPO,
  TIPOS_DO_ITEM,
  mensagemDoErro,
  useCarregarLeitura,
  useFilaDaConferencia,
  type ContadoresDaFila,
  type ItemDaFila,
  type ResumoDaCarga,
  type SituacaoDoItem,
} from "../lib/catalogoConferencia";
import { DA_LISTA, useChegouPeloHistorico } from "../lib/navegacao";

const COR_DA_SITUACAO: Record<SituacaoDoItem, "neutral" | "green" | "gold"> = {
  a_conferir: "neutral",
  conferido: "green",
  sem_leitura: "gold",
};
const SITUACOES: SituacaoDoItem[] = ["a_conferir", "conferido", "sem_leitura"];
const FILTRO =
  "h-11 rounded-full border px-4 text-sm font-medium transition-colors";

function plural(quantidade: number, um: string, varios: string): string {
  return `${quantidade} ${quantidade === 1 ? um : varios}`;
}

function textoDaCarga(resumo: ResumoDaCarga): string {
  const partes = [
    resumo.itens_novos > 0
      ? `Leitura carregada: ${plural(resumo.itens_novos, "item", "itens")} e ${plural(resumo.personagens_novos, "personagem", "personagens")}.`
      : "Nenhum item novo na leitura.",
  ];
  if (resumo.ignorados.length > 0) {
    partes.push(`${plural(resumo.ignorados.length, "item ignorado", "itens ignorados")}: não existem mais no catálogo.`);
  }
  return partes.join(" ");
}

function Progresso({ contadores, continuar }: { contadores: ContadoresDaFila; continuar: string | null }) {
  const comLeitura = contadores.a_conferir + contadores.conferidos;
  const porcento = comLeitura ? Math.round((contadores.conferidos / comLeitura) * 100) : 0;
  return (
    <section className="space-y-3 rounded-lg border border-line bg-panel p-4" aria-label="Progresso da conferência">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-lg font-semibold text-ink">
          {contadores.conferidos} de {comLeitura} conferidos
        </p>
        <span className="text-sm tabular-nums text-muted">{porcento}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-2" aria-hidden>
        {/* Largura vinda do dado: único uso de `style` da tela (mesmo caso do HomePerformance). */}
        <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${porcento}%` }} />
      </div>
      {contadores.sem_leitura > 0 && (
        <p className="text-sm text-muted">
          {plural(contadores.sem_leitura, "item sem leitura das fotos", "itens sem leitura das fotos")}, fora desta conta.
        </p>
      )}
      {comLeitura > 0 && contadores.a_conferir === 0 && (
        <p className="text-sm font-medium text-green">Todos os itens da fila foram conferidos.</p>
      )}
      {continuar && (
        <Button asChild size="lg" className="w-full sm:w-auto">
          <Link to={continuar} state={DA_LISTA}>
            Continuar conferência
          </Link>
        </Button>
      )}
    </section>
  );
}

function LinhaDaFila({ item, busca }: { item: ItemDaFila; busca: string }) {
  const detalhes = [item.tipo ? ROTULO_DO_TIPO[item.tipo] : null];
  if (item.personagens > 0) detalhes.push(plural(item.personagens, "personagem", "personagens"));
  if (item.conferido_por) detalhes.push(`por ${item.conferido_por}`);
  return (
    <li>
      <Link
        to={{ pathname: `/admin/catalogo/conferencia/${item.id}`, search: busca }}
        state={DA_LISTA}
        className="flex min-h-16 items-center gap-3 px-3 py-2 transition-colors hover:bg-surface-2"
      >
        <Foto
          src={item.capa_url ? assetUrl(item.capa_url) : null}
          alt=""
          loading="lazy"
          className="h-12 w-12 shrink-0 rounded-md object-cover"
          fallback={<div className="h-12 w-12 shrink-0 rounded-md bg-surface-2" aria-hidden />}
        />
        <div className="min-w-0 flex-1">
          {/* Duas linhas, não reticências: "Alice … (Desenho)" e "Alice … (Live Action 1)" só diferem no fim. */}
          <p className="line-clamp-2 text-sm font-medium text-ink">{item.nome}</p>
          <p className="truncate text-xs text-muted">{detalhes.filter(Boolean).join(" · ")}</p>
        </div>
        <Badge tone={COR_DA_SITUACAO[item.situacao]}>{ROTULO_DA_SITUACAO[item.situacao]}</Badge>
      </Link>
    </li>
  );
}

/**
 * Fila da conferência de personagens do catálogo (feature 360).
 *
 * A fila é calculada no servidor a cada consulta, contra o catálogo de agora: item que ganhou elenco
 * ou ficha some sozinho, item novo aparece como "Sem leitura". Os contadores são sempre os da fila
 * inteira; os filtros e a busca moram no endereço e seguem para a tela do item, para o "próximo"
 * respeitar o mesmo recorte.
 */
export function CatalogoConferenciaPage() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const tipo = params.get("tipo") ?? "";
  const situacao = params.get("situacao") ?? "";
  const q = params.get("q") ?? "";

  function setFiltros(mudancas: Record<string, string | null>) {
    setParams(
      (atual) => {
        const proximo = new URLSearchParams(atual);
        for (const [chave, valor] of Object.entries(mudancas)) {
          if (valor) proximo.set(chave, valor);
          else proximo.delete(chave);
        }
        return proximo;
      },
      { replace: true, state: location.state },
    );
  }

  // A pausa vale só para o que vai ao servidor; o campo responde a cada tecla.
  const [buscaComPausa, setBuscaComPausa] = useState(() => q.trim());
  useEffect(() => {
    const espera = setTimeout(() => setBuscaComPausa(q.trim()), 300);
    return () => clearTimeout(espera);
  }, [q]);

  const query = useFilaDaConferencia({
    tipo: tipo || undefined,
    situacao: situacao || undefined,
    q: buscaComPausa || undefined,
  });
  const carregar = useCarregarLeitura();
  const voltou = useChegouPeloHistorico();
  useRestaurarRolagem(location.key, { restaurar: voltou, pronto: Boolean(query.data) });

  const dados = query.data;
  const itens = dados?.itens ?? [];
  const atualizando = query.isPlaceholderData || buscaComPausa !== q.trim();
  const primeiroAConferir = itens.find((item) => item.situacao === "a_conferir");
  const continuar = primeiroAConferir
    ? `/admin/catalogo/conferencia/${primeiroAConferir.id}${location.search}`
    : null;
  const aCarregar = dados?.leitura?.a_carregar ?? 0;
  const nadaCarregado = dados ? dados.contadores.a_conferir + dados.contadores.conferidos === 0 : false;

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 pb-24 sm:p-6">
      <PageHeader
        title="Conferência de personagens"
        subtitle="Confira o que a leitura das fotos propôs para cada item do catálogo. Cada decisão é salva na hora."
        className="mb-0"
        breadcrumbs={[{ label: "Catálogo", href: "/admin/catalogo" }, { label: "Conferência de personagens" }]}
        renderCrumb={(crumb, className) => (
          <Link to={crumb.href ?? "/admin/catalogo"} className={className}>
            {crumb.label}
          </Link>
        )}
      />

      {query.isPending && (
        <div className="space-y-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="space-y-2 rounded-lg border border-line bg-panel p-4">
          <p className="text-sm text-red">Não foi possível carregar a fila. Tente novamente.</p>
          <Button variant="outline" onClick={() => query.refetch()}>
            Tentar novamente
          </Button>
        </div>
      )}

      {dados && (
        <>
          <Progresso contadores={dados.contadores} continuar={continuar} />

          {(aCarregar > 0 || carregar.data || carregar.error) && (
            <section className="space-y-2 rounded-lg border border-line bg-panel p-4" aria-label="Leitura das fotos">
              {aCarregar > 0 && (
                <>
                  <p className="text-sm text-ink">
                    {nadaCarregado
                      ? "A leitura das fotos ainda não foi carregada."
                      : `${plural(aCarregar, "item tem", "itens têm")} leitura das fotos pronta para carregar.`}
                  </p>
                  <Button variant="outline" loading={carregar.isPending} onClick={() => carregar.mutate()}>
                    Carregar leitura
                  </Button>
                </>
              )}
              {carregar.data && <p className="text-sm text-muted">{textoDaCarga(carregar.data)}</p>}
              {carregar.error && <p className="text-sm text-red">{mensagemDoErro(carregar.error)}</p>}
            </section>
          )}

          <div className="space-y-2">
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tipo">
              <button
                type="button"
                aria-pressed={tipo === ""}
                onClick={() => setFiltros({ tipo: null })}
                className={cn(FILTRO, tipo === "" ? "border-accent bg-accent-soft text-accent" : "border-line bg-panel text-muted")}
              >
                Todos
              </button>
              {TIPOS_DO_ITEM.map((valor) => {
                const conta = dados.contadores.por_tipo[valor];
                return (
                  <button
                    key={valor}
                    type="button"
                    aria-pressed={tipo === valor}
                    onClick={() => setFiltros({ tipo: tipo === valor ? null : valor })}
                    className={cn(
                      FILTRO,
                      tipo === valor ? "border-accent bg-accent-soft text-accent" : "border-line bg-panel text-muted",
                    )}
                  >
                    {ROTULO_DO_TIPO[valor]}{" "}
                    <span className="tabular-nums">
                      {conta?.conferidos ?? 0}/{conta?.total ?? 0}
                    </span>
                  </button>
                );
              })}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                // `flex-1` só na linha (sm+): na coluna do celular ele zeraria a base e venceria o `h-11`.
                className="h-11 w-full min-w-0 shrink-0 rounded-md border border-line bg-panel px-3 text-sm text-ink sm:w-auto sm:flex-1"
                placeholder="Buscar pelo nome do item…"
                aria-label="Buscar pelo nome do item"
                value={q}
                onChange={(e) => setFiltros({ q: e.target.value || null })}
              />
              <select
                className="h-11 rounded-md border border-line bg-panel px-3 text-sm text-ink"
                aria-label="Filtrar por situação"
                value={situacao}
                onChange={(e) => setFiltros({ situacao: e.target.value || null })}
              >
                <option value="">Todas as situações</option>
                {SITUACOES.map((valor) => (
                  <option key={valor} value={valor}>
                    {ROTULO_DA_SITUACAO[valor]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={cn("transition-opacity", atualizando && "opacity-60")} aria-busy={atualizando}>
            <p className="mb-2 text-xs text-muted">{plural(itens.length, "item", "itens")} nesta lista</p>
            {itens.length === 0 ? (
              <p className="rounded-lg border border-line bg-panel p-4 text-sm text-muted">Nenhum item encontrado.</p>
            ) : (
              <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-panel">
                {itens.map((item) => (
                  <LinhaDaFila key={item.id} item={item} busca={location.search} />
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
