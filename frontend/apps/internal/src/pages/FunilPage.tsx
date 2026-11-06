import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
  cn,
} from "@manto/ui";
import { IconeDoCanal } from "../components/conversas/IconeDoCanal";
import type { Canal } from "../lib/conversas";
import {
  PRESETS_DO_PERIODO,
  datasDoPreset,
  useFunil,
  useParados,
  type DivisaoDoFunil,
  type EtapaContada,
  type EtapaDoFunil,
  type FiltrosDoFunil,
  type Funil,
  type PresetDoPeriodo,
} from "../lib/funil";

const DIVISOES: { valor: DivisaoDoFunil; rotulo: string }[] = [
  { valor: "vendedor", rotulo: "Vendedor" },
  { valor: "campanha", rotulo: "Campanha" },
  { valor: "canal", rotulo: "Canal" },
];

function porcento(valor: number | null): string {
  return valor === null
    ? "—"
    : `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function dataCurta(iso: string): string {
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

function diaDoContato(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    timeZone: "America/Sao_Paulo",
  });
}

/** As etapas como barras tocáveis: a largura é a parte de "Chegou"; o toque abre quem parou ali. */
function EtapasDoFunil({
  etapas,
  escolhida,
  onEscolher,
}: {
  etapas: EtapaContada[];
  escolhida: EtapaDoFunil | null;
  onEscolher: (etapa: EtapaDoFunil) => void;
}) {
  return (
    <ol className="space-y-1.5" aria-label="Etapas do funil">
      {etapas.map((etapa, i) => {
        const ativa = escolhida === etapa.chave;
        return (
          <li key={etapa.chave}>
            <button
              type="button"
              onClick={() => onEscolher(etapa.chave)}
              aria-pressed={ativa}
              className={cn(
                // O trilho da barra tem a mesma largura em todas as etapas, senão a comparação
                // mente: no celular ele ocupa uma linha inteira, abaixo do nome e do número.
                "grid w-full grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1.5 rounded-md px-2 py-2 text-left text-sm transition-colors sm:grid-cols-[10rem_1fr_9rem] sm:gap-y-0",
                ativa ? "bg-accent-soft" : "hover:bg-surface-2",
              )}
            >
              <span className="font-medium text-ink">{etapa.rotulo}</span>
              <span className="order-last col-span-2 h-3 overflow-hidden rounded-full bg-surface-2 sm:order-none sm:col-span-1">
                <span
                  className="block h-full rounded-full bg-accent"
                  style={{
                    width: `${Math.max(etapa.sobre_chegou ?? 0, etapa.quantidade ? 2 : 0)}%`,
                  }}
                />
              </span>
              <span className="text-right tabular-nums">
                <span className="font-semibold text-ink">
                  {etapa.quantidade}
                </span>{" "}
                <span className="text-xs text-muted">
                  {porcento(etapa.sobre_chegou)}
                </span>
                {i > 0 && (
                  <span className="block text-[11px] text-muted">
                    {porcento(etapa.passagem)} da anterior
                  </span>
                )}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

function TabelaDaDivisao({ funil }: { funil: Funil }) {
  if (funil.grupos.length === 0) return null;
  return (
    <div className="-mx-4 overflow-x-auto px-4">
      <Table className="min-w-[640px]">
        <thead>
          <TableRow head>
            <TableCell as="th">
              {DIVISOES.find((d) => d.valor === funil.dividir)?.rotulo}
            </TableCell>
            {funil.etapas.map((etapa) => (
              <TableCell key={etapa.chave} as="th" align="right">
                {etapa.rotulo}
              </TableCell>
            ))}
            <TableCell as="th" align="right">
              Conversão
            </TableCell>
          </TableRow>
        </thead>
        <tbody>
          {funil.grupos.map((grupo) => (
            <TableRow key={grupo.chave}>
              <TableCell className="font-medium text-ink">
                {grupo.rotulo}
              </TableCell>
              {funil.etapas.map((etapa) => (
                <TableCell
                  key={etapa.chave}
                  align="right"
                  className="tabular-nums"
                >
                  {grupo.quantidades[etapa.chave]}
                </TableCell>
              ))}
              <TableCell align="right" className="tabular-nums">
                {porcento(grupo.conversao)}
              </TableCell>
            </TableRow>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

function QuemParou({
  filtros,
  etapa,
}: {
  filtros: FiltrosDoFunil;
  etapa: EtapaDoFunil;
}) {
  const query = useParados(filtros, etapa);
  const dados = query.data;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Pararam em: {dados?.rotulo ?? "…"}</CardTitle>
      </CardHeader>
      <CardContent>
        {query.isLoading && <Skeleton className="h-24 w-full" />}
        {query.isError && (
          <p className="text-sm text-red" role="alert">
            Não foi possível carregar a lista. Tente novamente.
          </p>
        )}
        {dados && dados.total === 0 && (
          <p className="text-sm text-muted">
            Nenhuma conversa parou nesta etapa.
          </p>
        )}
        {dados && dados.conversas.length > 0 && (
          <>
            <ul className="divide-y divide-line">
              {dados.conversas.map((conversa) => (
                <li
                  key={conversa.id}
                  className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="flex min-w-0 items-center gap-1.5 font-medium text-ink">
                      <IconeDoCanal canal={conversa.canal} />
                      <span className="truncate">{conversa.nome}</span>
                    </p>
                    <p className="text-xs text-muted">
                      Chegou em {diaDoContato(conversa.primeiro_contato)} ·{" "}
                      {conversa.vendedor ?? "Sem responsável"} ·{" "}
                      {conversa.campanha}
                    </p>
                  </div>
                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                  >
                    <Link to={`/conversas?c=${conversa.id}`}>
                      Abrir conversa
                    </Link>
                  </Button>
                </li>
              ))}
            </ul>
            {dados.total > dados.conversas.length && (
              <p className="mt-2 text-xs text-muted">
                Mostrando as {dados.conversas.length} mais recentes de{" "}
                {dados.total}.
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * O funil das conversas (`/funil`, feature 335): as conversas novas do período e até onde cada uma
 * chegou — Chegou, Orçamento enviado, Formulário, Evento fechado, Pagou, Avaliou —, por vendedor,
 * campanha ou canal, e quem parou em cada etapa para o vendedor retomar. Derivado dos fatos: não há
 * cartão para arrastar (a lição da feature 021).
 */
export function FunilPage() {
  const [preset, setPreset] = useState<PresetDoPeriodo>("mes_atual");
  const [personalizado, setPersonalizado] = useState(() =>
    datasDoPreset("mes_atual")!,
  );
  const [canal, setCanal] = useState<Canal | null>(null);
  const [campanha, setCampanha] = useState<string | null>(null);
  const [dividir, setDividir] = useState<DivisaoDoFunil>("vendedor");
  const [etapa, setEtapa] = useState<EtapaDoFunil | null>(null);

  const datas = datasDoPreset(preset) ?? personalizado;
  // A campanha escolhida pode não existir no novo período ou canal: o filtro volta para "Todas", senão
  // o funil zeraria com o seletor mostrando "Todas as campanhas".
  const trocarPeriodo = (novo: PresetDoPeriodo) => {
    setPreset(novo);
    setCampanha(null);
  };
  const filtros: FiltrosDoFunil = { ...datas, canal, campanha };
  const query = useFunil(filtros, dividir);
  const funil = query.data;

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4 sm:p-6">
      <PageHeader title="Funil" className="mb-0" />
      <p className="text-sm text-muted">
        As conversas novas do período e até onde cada uma chegou. Toque numa
        etapa para ver quem parou nela.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-panel p-1">
          {PRESETS_DO_PERIODO.map((opcao) => (
            <Button
              key={opcao.valor}
              size="sm"
              variant={preset === opcao.valor ? "default" : "ghost"}
              onClick={() => trocarPeriodo(opcao.valor)}
              aria-pressed={preset === opcao.valor}
            >
              {opcao.rotulo}
            </Button>
          ))}
        </div>
        {preset === "personalizado" && (
          <div className="flex items-center gap-1 text-sm">
            <input
              type="date"
              value={personalizado.inicio}
              max={personalizado.fim}
              onChange={(e) => {
                if (!e.target.value) return;
                setPersonalizado((p) => ({ ...p, inicio: e.target.value }));
                setCampanha(null);
              }}
              className="h-9 rounded-md border border-line bg-panel px-2 text-ink"
              aria-label="Data inicial"
            />
            <span className="text-muted">a</span>
            <input
              type="date"
              value={personalizado.fim}
              min={personalizado.inicio}
              onChange={(e) => {
                if (!e.target.value) return;
                setPersonalizado((p) => ({ ...p, fim: e.target.value }));
                setCampanha(null);
              }}
              className="h-9 rounded-md border border-line bg-panel px-2 text-ink"
              aria-label="Data final"
            />
          </div>
        )}
        <select
          value={canal ?? ""}
          onChange={(e) => {
            setCanal((e.target.value || null) as Canal | null);
            setCampanha(null);
          }}
          className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          aria-label="Filtrar por canal"
        >
          <option value="">Todos os canais</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="instagram">Instagram</option>
        </select>
        <select
          value={campanha ?? ""}
          onChange={(e) => setCampanha(e.target.value || null)}
          className="h-9 max-w-[16rem] rounded-md border border-line bg-panel px-2 text-sm text-ink"
          aria-label="Filtrar por campanha"
        >
          <option value="">Todas as campanhas</option>
          {campanha &&
            funil &&
            !funil.campanhas.some((opcao) => opcao.valor === campanha) && (
              <option value={campanha}>
                {campanha.startsWith("__") ? "Sem anúncio" : campanha} (0)
              </option>
            )}
          {funil?.campanhas.map((opcao) => (
            <option key={opcao.valor} value={opcao.valor}>
              {opcao.rotulo} ({opcao.quantidade})
            </option>
          ))}
        </select>
        {funil && (
          <span className="text-xs text-muted">
            {dataCurta(funil.periodo.inicio)} a {dataCurta(funil.periodo.fim)}
          </span>
        )}
      </div>

      {query.isLoading && <Skeleton className="h-64 w-full" />}
      {query.isError && (
        <div
          className="rounded-md bg-red-soft px-4 py-3 text-sm text-red"
          role="alert"
        >
          Não foi possível carregar o funil. Tente novamente.
        </div>
      )}

      {/* Trocando o filtro, o funil anterior fica (sem piscar), mas apagado até o novo chegar. */}
      <div
        aria-busy={query.isPlaceholderData}
        className={cn(
          "space-y-4 transition-opacity",
          query.isPlaceholderData && "opacity-60",
        )}
      >
        {funil && funil.total === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted">
              Nenhuma conversa nova neste período. Tente outro período ou tire
              os filtros.
            </CardContent>
          </Card>
        )}

        {funil && funil.total > 0 && (
          <>
            <Card>
              <CardHeader>
                <CardTitle>
                  {funil.total}{" "}
                  {funil.total === 1 ? "conversa nova" : "conversas novas"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <EtapasDoFunil
                  etapas={funil.etapas}
                  escolhida={etapa}
                  onEscolher={(e) =>
                    setEtapa((atual) => (atual === e ? null : e))
                  }
                />
              </CardContent>
            </Card>

            {etapa && <QuemParou filtros={filtros} etapa={etapa} />}

            <Card>
              <CardHeader className="flex-row flex-wrap items-center justify-between gap-2 space-y-0">
                <CardTitle>
                  Por{" "}
                  {DIVISOES.find(
                    (d) => d.valor === dividir,
                  )?.rotulo.toLowerCase()}
                </CardTitle>
                <div className="flex gap-1 rounded-lg border border-line bg-panel p-1">
                  {DIVISOES.map((opcao) => (
                    <Button
                      key={opcao.valor}
                      size="sm"
                      variant={dividir === opcao.valor ? "default" : "ghost"}
                      onClick={() => setDividir(opcao.valor)}
                      aria-pressed={dividir === opcao.valor}
                    >
                      {opcao.rotulo}
                    </Button>
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                <TabelaDaDivisao funil={funil} />
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
