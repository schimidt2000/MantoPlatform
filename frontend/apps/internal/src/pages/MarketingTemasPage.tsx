import { useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { AvatarThumb, Badge, Button, Card, Input, PageHeader, Skeleton } from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import {
  LIBERADO_LABELS,
  LICENCA_ORIGEM_LABELS,
  useConfirmarSugestoes,
  useMarcarLicenca,
  useTemasLicenca,
  type LiberadoAnuncio,
  type LicencaOrigem,
  type TemaLicenca,
} from "../lib/marketing";

const SELECT = "h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink";

const LIBERADO_TONE: Record<LiberadoAnuncio, "green" | "red" | "neutral"> = {
  sim: "green",
  nao: "red",
  nao_decidido: "neutral",
};

function LinhaTema({
  tema,
  podeLiberarLicenciado,
  marcado,
  onMarcar,
}: {
  tema: TemaLicenca;
  podeLiberarLicenciado: boolean;
  marcado: boolean;
  onMarcar: (marcado: boolean) => void;
}) {
  const marcar = useMarcarLicenca();
  const erro =
    marcar.error instanceof ApiRequestError ? marcar.error.message : marcar.error ? "Não foi possível salvar." : null;
  // Liberar licenciado é do Superadmin (o servidor recusa os outros com 403) — a tela nem oferece.
  const podeLiberar = tema.licenca_origem !== "nao_classificado" && (tema.licenca_origem === "autoral" || podeLiberarLicenciado);

  return (
    <li className="flex flex-col gap-2 py-2.5 sm:flex-row sm:items-center sm:gap-3">
      <div className="flex min-w-0 flex-1 items-center gap-3">
      {tema.licenca_sugestao ? (
        <input
          type="checkbox"
          className="h-4 w-4 accent-accent"
          aria-label={`Selecionar ${tema.name}`}
          checked={marcado}
          onChange={(e) => onMarcar(e.target.checked)}
        />
      ) : (
        <span className="w-4" aria-hidden />
      )}
      <AvatarThumb src={assetUrl(tema.cover_url)} name={tema.name} shape="square" size="md" fallbackIcon="🎭" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">{tema.name}</p>
        {tema.licenca_sugestao && (
          <p className="text-xs text-muted">
            Sugestão da rotina: <strong className="text-ink">{LICENCA_ORIGEM_LABELS[tema.licenca_sugestao]}</strong>
            {tema.licenca_sugestao_motivo ? ` — ${tema.licenca_sugestao_motivo}` : ""}
          </p>
        )}
        {erro && (
          <p className="text-xs text-red" role="alert">
            {erro}
          </p>
        )}
      </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 pl-7 sm:pl-0">
      <select
        aria-label={`Origem de ${tema.name}`}
        className={SELECT}
        value={tema.licenca_origem}
        disabled={marcar.isPending}
        onChange={(e) => marcar.mutate({ id: tema.id, input: { licenca_origem: e.target.value as LicencaOrigem } })}
      >
        {(Object.keys(LICENCA_ORIGEM_LABELS) as LicencaOrigem[]).map((o) => (
          <option key={o} value={o}>
            {LICENCA_ORIGEM_LABELS[o]}
          </option>
        ))}
      </select>
      <Badge tone={LIBERADO_TONE[tema.liberado_anuncio]}>{LIBERADO_LABELS[tema.liberado_anuncio]}</Badge>
      {tema.liberado_anuncio === "sim" ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={marcar.isPending}
          onClick={() => marcar.mutate({ id: tema.id, input: { liberado_anuncio: "nao" } })}
        >
          Tirar do anúncio
        </Button>
      ) : (
        podeLiberar && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={marcar.isPending}
            onClick={() => marcar.mutate({ id: tema.id, input: { liberado_anuncio: "sim" } })}
          >
            Liberar para anúncio
          </Button>
        )
      )}
      </div>
    </li>
  );
}

/**
 * Temas e licença (feature 345): o que pode ir para anúncio.
 *
 * Duas marcações por tema — a origem (autoral ou licenciado) e o "liberado para anúncio". O
 * autoral confirmado já sai liberado; o licenciado sai não liberado e só o Superadmin libera caso a
 * caso. Tema não classificado nunca vai para anúncio (risco jurídico).
 */
export function MarketingTemasPage() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const filtros = {
    q: params.get("q") ?? "",
    origem: (params.get("origem") ?? "") as LicencaOrigem | "",
    liberado: (params.get("liberado") ?? "") as LiberadoAnuncio | "",
    sugestao: params.get("sugestao") === "1",
    pagina: Math.max(1, Number(params.get("pagina")) || 1),
  };
  const query = useTemasLicenca(filtros);
  const confirmar = useConfirmarSugestoes();
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set());
  const [aviso, setAviso] = useState<string | null>(null);

  // Feature 351: a página mora no endereço com os filtros; mudar um filtro volta à página 1.
  function setFiltro(chave: string, valor: string | null) {
    setParams(
      (atual) => {
        const proximo = new URLSearchParams(atual);
        if (valor) proximo.set(chave, valor);
        else proximo.delete(chave);
        if (chave !== "pagina") proximo.delete("pagina");
        return proximo;
      },
      { replace: true, state: location.state },
    );
    setSelecionados(new Set());
  }

  const paginas = query.data?.paginas ?? 1;
  const pagina = query.data?.pagina ?? filtros.pagina;
  const topoDaLista = useRef<HTMLDivElement>(null);

  // Trocar de página com o botão do rodapé leva ao topo da lista nova (senão a pessoa cai no fim dela).
  function irParaPagina(numero: number) {
    setFiltro("pagina", String(numero));
    topoDaLista.current?.scrollIntoView({ block: "start" });
  }

  const itens = query.data?.items ?? [];
  const comSugestao = itens.filter((t) => t.licenca_sugestao);

  function confirmarSelecionados(ids: number[]) {
    setAviso(null);
    confirmar.mutate(ids, {
      onSuccess: (r) => {
        setSelecionados(new Set());
        setAviso(`${r.confirmados} tema(s) confirmado(s).`);
      },
    });
  }

  return (
    <div className="w-full px-4 py-6 sm:px-8">
      <PageHeader
        title="Temas e licença"
        subtitle="O que pode ir para anúncio. Licenciado só vai se o Superadmin liberar; não classificado nunca vai."
      />

      {query.data && (
        <div className="mb-4 flex flex-wrap gap-2 text-sm">
          <Badge tone="green">Autoral: {query.data.contagem.autoral}</Badge>
          <Badge tone="gold">Licenciado: {query.data.contagem.licenciado}</Badge>
          <Badge tone="neutral">Não classificado: {query.data.contagem.nao_classificado}</Badge>
          {query.data.com_sugestao > 0 && <Badge tone="accent">{query.data.com_sugestao} com sugestão da rotina</Badge>}
        </div>
      )}

      <Card className="mb-3 flex flex-wrap items-center gap-2 px-4 py-3">
        <Input
          type="search"
          aria-label="Buscar tema"
          placeholder="🔍 Buscar tema…"
          className="h-9 w-full sm:w-64"
          value={filtros.q}
          onChange={(e) => setFiltro("q", e.target.value || null)}
        />
        <select aria-label="Filtrar por origem" className={SELECT} value={filtros.origem} onChange={(e) => setFiltro("origem", e.target.value || null)}>
          <option value="">Toda origem</option>
          {(Object.keys(LICENCA_ORIGEM_LABELS) as LicencaOrigem[]).map((o) => (
            <option key={o} value={o}>
              {LICENCA_ORIGEM_LABELS[o]}
            </option>
          ))}
        </select>
        <select aria-label="Filtrar por liberado" className={SELECT} value={filtros.liberado} onChange={(e) => setFiltro("liberado", e.target.value || null)}>
          <option value="">Liberado ou não</option>
          {(Object.keys(LIBERADO_LABELS) as LiberadoAnuncio[]).map((o) => (
            <option key={o} value={o}>
              {LIBERADO_LABELS[o]}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-ink">
          <input
            type="checkbox"
            className="h-4 w-4 accent-accent"
            checked={filtros.sugestao}
            onChange={(e) => setFiltro("sugestao", e.target.checked ? "1" : null)}
          />
          Só com sugestão
        </label>
      </Card>

      {comSugestao.length > 0 && (
        <Card className="mb-3 flex flex-wrap items-center gap-2 border-accent/40 px-4 py-3">
          <p className="mr-auto text-sm text-ink">
            {selecionados.size > 0
              ? `${selecionados.size} selecionado(s) para confirmar a sugestão.`
              : `${comSugestao.length} tema(s) nesta página com sugestão da rotina.`}
          </p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={confirmar.isPending}
            onClick={() => confirmarSelecionados(comSugestao.map((t) => t.id))}
          >
            Confirmar as sugestões desta página
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={confirmar.isPending || selecionados.size === 0}
            onClick={() => confirmarSelecionados([...selecionados])}
          >
            {confirmar.isPending ? "Confirmando…" : "Confirmar selecionados"}
          </Button>
        </Card>
      )}
      {aviso && <p className="mb-3 text-sm text-green">{aviso}</p>}
      {confirmar.isError && (
        <p className="mb-3 text-sm text-red" role="alert">
          Não foi possível confirmar. Tente de novo.
        </p>
      )}

      <div ref={topoDaLista} className="scroll-mt-20" />
      {query.isLoading && <Skeleton className="h-64 w-full" />}
      {query.isError && (
        <p className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os temas.
        </p>
      )}
      {query.data && (
        <Card className={`px-4 transition-opacity ${query.isPlaceholderData ? "opacity-60" : ""}`}>
          {itens.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">Nenhum tema com esses filtros.</p>
          ) : (
            <ul className="divide-y divide-line">
              {itens.map((tema) => (
                <LinhaTema
                  key={tema.id}
                  tema={tema}
                  podeLiberarLicenciado={query.data.pode_liberar_licenciado}
                  marcado={selecionados.has(tema.id)}
                  onMarcar={(m) =>
                    setSelecionados((s) => {
                      const novo = new Set(s);
                      if (m) novo.add(tema.id);
                      else novo.delete(tema.id);
                      return novo;
                    })
                  }
                />
              ))}
            </ul>
          )}
        </Card>
      )}
      {query.data && paginas > 1 && (
        <nav className="mt-3 flex items-center justify-between gap-2" aria-label="Páginas dos temas">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={pagina <= 1 || query.isFetching}
            onClick={() => irParaPagina(pagina - 1)}
          >
            Anterior
          </Button>
          <span className="text-sm text-muted">
            Página {pagina} de {paginas} · {(query.data.total ?? 0).toLocaleString("pt-BR")} temas
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={pagina >= paginas || query.isFetching}
            onClick={() => irParaPagina(pagina + 1)}
          >
            Próxima
          </Button>
        </nav>
      )}
    </div>
  );
}
