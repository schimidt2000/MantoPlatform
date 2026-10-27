import { useEffect, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { Button, PageHeader, Skeleton, useRestaurarRolagem } from "@manto/ui";
import { useEmailBounces, useTalentDirectory } from "../lib/talents";
import { useCurrentUser } from "../lib/useAuth";
import { BounceQueue } from "../components/BounceQueue";
import { TalentMosaic } from "../components/TalentMosaic";
import {
  EMPTY_ADVANCED_FILTERS,
  TalentFilterPanel,
  type TalentAdvancedFilters,
} from "../components/TalentFilterPanel";
import { useChegouPeloHistorico } from "../lib/navegacao";

/** Aba visível: as duas do diretório, mais a fila de emails devolvidos (feature 219). */
type View = "active" | "pending" | "bounces";

/** Filtros de lista no endereço com o MESMO nome do parâmetro da API (`lib/talents.ts`). */
const FILTROS_DE_LISTA = ["language", "race", "top", "bottom", "shoe", "passport", "tag"] as const;

function filtrosDaUrl(params: URLSearchParams): TalentAdvancedFilters {
  const op = params.get("height_op");
  return {
    ...EMPTY_ADVANCED_FILTERS,
    ...Object.fromEntries(FILTROS_DE_LISTA.map((chave) => [chave, params.getAll(chave)])),
    character: params.get("character") ?? "",
    heightOp: op === "lte" || op === "eq" ? op : "gte",
    heightValue: params.get("height_value") ?? "",
    jaTrabalhou: params.get("ja_trabalhou") === "1",
  };
}

function temFiltroAvancado(f: TalentAdvancedFilters): boolean {
  return (
    f.jaTrabalhou ||
    Boolean(f.character) ||
    Boolean(f.heightValue) ||
    FILTROS_DE_LISTA.some((chave) => f[chave].length > 0)
  );
}

export function TalentsListPage() {
  // Aba, busca, página e filtros no endereço (feature 320): voltar da ficha devolve a mesma lista,
  // e o `?status=pending` que a ficha já mandava passa a valer. Sempre `replace`: mudar filtro
  // não cria um passo de "voltar".
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const status: "active" | "pending" = params.get("status") === "pending" ? "pending" : "active";
  // `view` é separado de `status` de propósito: alternar para a fila não pode refazer a busca do
  // diretório, senão voltar para "Ativos" perderia página, busca e filtros aplicados.
  const view: View = params.get("aba") === "emails" ? "bounces" : status;
  const q = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("pagina")) || 1);
  const filters = filtrosDaUrl(params);
  const [showFilters, setShowFilters] = useState(() => temFiltroAvancado(filters));

  function mudar(mudancas: Record<string, string | string[] | null>) {
    setParams(
      (atual) => {
        const proximo = new URLSearchParams(atual);
        for (const [chave, valor] of Object.entries(mudancas)) {
          proximo.delete(chave);
          for (const v of Array.isArray(valor) ? valor : [valor]) if (v) proximo.append(chave, v);
        }
        return proximo;
      },
      { replace: true, state: location.state },
    );
  }
  const setPage = (valor: number) => mudar({ pagina: valor > 1 ? String(valor) : null });

  const { data: me } = useCurrentUser();
  // A fila expõe telefone e email de quem contatar: mesmo gate do endpoint (CASTING/SUPERADMIN).
  const canSeeBounces = Boolean(me?.is_superadmin || me?.roles.includes("CASTING"));
  const bounces = useEmailBounces(canSeeBounces);
  const bounceCount = bounces.data?.pending_count ?? 0;

  const query = useTalentDirectory({
    status,
    q: q || undefined,
    ja_trabalhou: filters.jaTrabalhou,
    page,
    language: filters.language,
    race: filters.race,
    top: filters.top,
    bottom: filters.bottom,
    shoe: filters.shoe,
    passport: filters.passport,
    tag: filters.tag,
    height_op: filters.heightOp,
    height_value: filters.heightValue || undefined,
    character: filters.character || undefined,
  });

  const applyFilters = (next: TalentAdvancedFilters) => {
    mudar({
      ...Object.fromEntries(FILTROS_DE_LISTA.map((chave) => [chave, next[chave]])),
      character: next.character || null,
      height_op: next.heightValue && next.heightOp !== "gte" ? next.heightOp : null,
      height_value: next.heightValue || null,
      ja_trabalhou: next.jaTrabalhou ? "1" : null,
      pagina: null,
    });
  };

  // Página que deixou de existir (talentos saíram do filtro enquanto a pessoa estava na ficha):
  // mostra a última que existe.
  const totalPaginas = query.data?.pages;
  useEffect(() => {
    if (totalPaginas && page > totalPaginas) setPage(totalPaginas);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totalPaginas, page]);

  const voltou = useChegouPeloHistorico();
  useRestaurarRolagem(location.key, { restaurar: voltou, pronto: Boolean(query.data) });

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6">
      <PageHeader title="Talentos" className="mb-4" />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {/* `on-color` no segmento ativo: o acento clareia no tema escuro e o `text-white` que
            estava aqui cairia para 2.72:1. `line-strong` porque a moldura é a única pista de
            que os dois botões formam um grupo segmentado (WCAG 1.4.11). */}
        <div className="flex rounded-md border border-line-strong">
          <button
            className={`px-3 py-1.5 text-sm ${view === "active" ? "bg-accent text-on-color" : "text-ink"}`}
            onClick={() => mudar({ status: null, aba: null, pagina: null })}
          >
            Ativos
          </button>
          <button
            className={`px-3 py-1.5 text-sm ${view === "pending" ? "bg-accent text-on-color" : "text-ink"}`}
            onClick={() => mudar({ status: "pending", aba: null, pagina: null })}
          >
            Pendentes {query.data && query.data.pending_count > 0 && `(${query.data.pending_count})`}
          </button>
          {canSeeBounces && (
            <button
              className={`px-3 py-1.5 text-sm ${view === "bounces" ? "bg-accent text-on-color" : "text-ink"}`}
              onClick={() => mudar({ aba: "emails" })}
            >
              E-mails com problema {bounceCount > 0 && `(${bounceCount})`}
            </button>
          )}
        </div>
        {view !== "bounces" && (
          <>
            <input
              className="h-10 min-w-40 flex-1 rounded-md border border-line bg-panel px-3 text-sm text-ink"
              placeholder="Buscar por nome ou nome artístico…"
              value={q}
              onChange={(e) => mudar({ q: e.target.value || null, pagina: null })}
              aria-label="Buscar talento"
            />
            {view === "active" && (
              <Button variant="outline" size="sm" onClick={() => setShowFilters((v) => !v)}>
                Filtros
              </Button>
            )}
          </>
        )}
      </div>

      {view === "bounces" && <BounceQueue />}

      {view === "active" && showFilters && (
        <div className="mb-4">
          <TalentFilterPanel
            filterOptions={query.data?.filter_options}
            applied={filters}
            onApply={applyFilters}
          />
        </div>
      )}

      {view !== "bounces" && query.isLoading && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {Array.from({ length: 12 }, (_, i) => (
            <Skeleton key={i} className="aspect-[3/4] w-full" />
          ))}
        </div>
      )}

      {view !== "bounces" && query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os talentos.
        </div>
      )}

      {view !== "bounces" && query.data && (
        <>
          {query.data.items.length === 0 ? (
            <p className="text-sm text-muted">Nenhum talento encontrado.</p>
          ) : (
            <TalentMosaic talents={query.data.items} isPending={status === "pending"} />
          )}

          {query.data.pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                ‹ Anterior
              </Button>
              <span className="text-sm text-muted">
                Página {query.data.page} de {query.data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= query.data.pages}
                onClick={() => setPage(page + 1)}
              >
                Próxima ›
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
