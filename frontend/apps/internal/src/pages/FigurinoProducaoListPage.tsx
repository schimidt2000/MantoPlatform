import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Plus, Shirt } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Input,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useGastosEventos } from "../lib/gastos";
import { useFigurinoSheets } from "../lib/figurino";
import {
  PRODUCAO_STATUS_LABELS,
  PRODUCAO_STATUS_TONES,
  prazoInfo,
  useCreateProducao,
  useProducoes,
  useResponsaveis,
  type Producao,
  type ProducaoKind,
  type ProducaoSeveridade,
  type ProducaoStatus,
} from "../lib/figurinoProducao";
import { useCurrentUser } from "../lib/useAuth";

const INPUT_CLASS = "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

const FILTROS: { key: string; label: string }[] = [
  { key: "abertos", label: "Em aberto" },
  { key: "solicitado", label: "Solicitados" },
  { key: "aprovado", label: "Aprovados" },
  { key: "em_producao", label: "Em produção" },
  { key: "pronto", label: "Prontos" },
  { key: "", label: "Tudo" },
];

/** Cabeçalho com os números que respondem "como está a oficina hoje". */
function Resumo({ itens }: { itens: Producao[] }) {
  const abertos = itens.filter((p) => p.is_open);
  const atrasados = abertos.filter((p) => p.is_late);
  const previsto = abertos.reduce((s, p) => s + (p.estimated_cost ?? 0), 0);
  const gasto = itens.reduce((s, p) => s + p.total_gasto, 0);

  const cards = [
    { label: "Em aberto", valor: String(abertos.length), tone: "" },
    {
      label: "Atrasados",
      valor: String(atrasados.length),
      tone: atrasados.length ? "text-red" : "",
    },
    { label: "Previsto (em aberto)", valor: formatBRL(previsto), tone: "" },
    { label: "Gasto lançado", valor: formatBRL(gasto), tone: "" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.label} className="px-4 py-3">
          <p className="text-xs text-muted">{c.label}</p>
          <p className={`mt-1 text-xl font-semibold text-ink ${c.tone}`}>{c.valor}</p>
        </Card>
      ))}
    </div>
  );
}

/** Formulário de abertura de pedido — qualquer papel interno pode usar (FR-012). */
function NovoPedidoDialog({
  open,
  onOpenChange,
  podeDesignar,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  podeDesignar: boolean;
}) {
  const criar = useCreateProducao();
  const responsaveis = useResponsaveis();
  const fichas = useFigurinoSheets();
  const [kind, setKind] = useState<ProducaoKind>("producao");
  const [severity, setSeverity] = useState<ProducaoSeveridade | "">("");
  const [fichaId, setFichaId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dataEvento, setDataEvento] = useState("");
  const [eventId, setEventId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [responsibleId, setResponsibleId] = useState("");
  const [estimated, setEstimated] = useState("");
  const [quantity, setQuantity] = useState("1");
  const eventos = useGastosEventos(dataEvento);

  const eManutencao = kind === "manutencao";

  const fichaOptions = useMemo(
    () =>
      (fichas.data?.items ?? []).map((f) => ({
        value: String(f.id),
        label: f.character_name,
      })),
    [fichas.data],
  );

  function fechar() {
    onOpenChange(false);
    setKind("producao");
    setSeverity("");
    setFichaId("");
    setTitle("");
    setDescription("");
    setDataEvento("");
    setEventId("");
    setDueDate("");
    setResponsibleId("");
    setEstimated("");
    setQuantity("1");
    criar.reset();
  }

  function salvar() {
    criar.mutate(
      {
        title,
        description: description || undefined,
        kind,
        severity: eManutencao ? (severity || null) : null,
        figurino_sheet_id: fichaId ? Number(fichaId) : null,
        event_id: eventId ? Number(eventId) : null,
        due_date: dueDate || null,
        responsible_id: responsibleId ? Number(responsibleId) : null,
        estimated_cost: estimated ? Number(estimated.replace(",", ".")) : null,
        quantity: Number(quantity) || 1,
      },
      { onSuccess: fechar },
    );
  }

  const podeSalvar =
    title.trim().length > 0 && (!eManutencao || (Boolean(fichaId) && Boolean(severity)));

  const erroCampo = (campo: string) =>
    (criar.error as { fields?: Record<string, string> } | null)?.fields?.[campo];

  return (
    <Dialog open={open} onOpenChange={(v) => (v ? onOpenChange(true) : fechar())}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Novo pedido de figurino</DialogTitle>
          <DialogDescription>
            {eManutencao
              ? "Conserto, ajuste ou adaptação de um figurino que já existe. A oficina assume direto — não precisa de aprovação."
              : "Uma peça nova, que ainda não existe. A oficina aprova e assume depois."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {/* O tipo vem primeiro porque muda o resto do formulário — e muda o fluxo. */}
          <div className="flex gap-2">
            {(["producao", "manutencao"] as ProducaoKind[]).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
                  kind === k
                    ? "border-accent bg-accent-soft font-medium text-accent"
                    : "border-line text-muted hover:bg-surface-2"
                }`}
              >
                {k === "producao" ? "Produzir peça nova" : "Consertar / ajustar"}
              </button>
            ))}
          </div>

          {eManutencao && (
            <>
              <div>
                <label className="text-xs text-muted" htmlFor="prod-ficha">
                  Qual figurino
                </label>
                <select
                  id="prod-ficha"
                  className={INPUT_CLASS}
                  value={fichaId}
                  onChange={(e) => setFichaId(e.target.value)}
                >
                  <option value="">Escolha a ficha…</option>
                  {fichaOptions.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </select>
                {erroCampo("figurino_sheet_id") && (
                  <p className="mt-1 text-xs text-red">{erroCampo("figurino_sheet_id")}</p>
                )}
              </div>

              <div>
                <span className="text-xs text-muted">Dá para usar assim como está?</span>
                <div className="mt-1 flex gap-2">
                  <button
                    type="button"
                    onClick={() => setSeverity("pode_esperar")}
                    className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
                      severity === "pode_esperar"
                        ? "border-gold bg-gold-soft font-medium text-gold-ink"
                        : "border-line text-muted hover:bg-surface-2"
                    }`}
                  >
                    Dá para usar
                  </button>
                  <button
                    type="button"
                    onClick={() => setSeverity("impede_uso")}
                    className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
                      severity === "impede_uso"
                        ? "border-red bg-red-soft font-medium text-red"
                        : "border-line text-muted hover:bg-surface-2"
                    }`}
                  >
                    Não pode ir para evento
                  </button>
                </div>
                <p className="mt-1 text-xs text-muted">
                  Marcado como “não pode ir”, o aviso aparece na ficha e no elenco de quem
                  escalar esse personagem.
                </p>
                {erroCampo("severity") && (
                  <p className="mt-1 text-xs text-red">{erroCampo("severity")}</p>
                )}
              </div>
            </>
          )}

          <div>
            <label className="text-xs text-muted" htmlFor="prod-title">
              {eManutencao ? "O que precisa ser resolvido" : "O que precisa ser feito"}
            </label>
            <Input
              id="prod-title"
              value={title}
              autoFocus
              placeholder={
                eManutencao
                  ? "Peça solta dentro do boneco"
                  : "Bermuda do Chapeleiro Maluco"
              }
              onChange={(e) => setTitle(e.target.value)}
            />
            {erroCampo("title") && <p className="mt-1 text-xs text-red">{erroCampo("title")}</p>}
          </div>

          <div>
            <label className="text-xs text-muted" htmlFor="prod-desc">
              {eManutencao
                ? "Detalhes (onde está, o que a pessoa relatou…)"
                : "Detalhes (tecido, medida, referência…)"}
            </label>
            <textarea
              id="prod-desc"
              className={`${INPUT_CLASS} h-20 py-2`}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted" htmlFor="prod-data-evento">
                Data do evento (opcional)
              </label>
              <input
                id="prod-data-evento"
                type="date"
                className={INPUT_CLASS}
                value={dataEvento}
                onChange={(e) => {
                  setDataEvento(e.target.value);
                  setEventId("");
                }}
              />
            </div>
            <div>
              <label className="text-xs text-muted" htmlFor="prod-evento">
                Evento
              </label>
              <select
                id="prod-evento"
                className={INPUT_CLASS}
                value={eventId}
                disabled={!dataEvento}
                onChange={(e) => setEventId(e.target.value)}
              >
                <option value="">Sem evento</option>
                {eventos.data?.events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Na manutenção, quantidade e custo somem: a maior parte não tem compra nenhuma — é
              trabalho manual. Custo previsto continua disponível, mas discreto. */}
          <div className={`grid gap-3 ${eManutencao ? "grid-cols-2" : "grid-cols-3"}`}>
            <div>
              <label className="text-xs text-muted" htmlFor="prod-prazo">
                Prazo
              </label>
              <input
                id="prod-prazo"
                type="date"
                className={INPUT_CLASS}
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
            {!eManutencao && (
              <div>
                <label className="text-xs text-muted" htmlFor="prod-qtd">
                  Quantidade
                </label>
                <Input
                  id="prod-qtd"
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
              </div>
            )}
            <div>
              <label className="text-xs text-muted" htmlFor="prod-custo">
                {eManutencao ? "Custo previsto (se houver)" : "Custo previsto"}
              </label>
              <Input
                id="prod-custo"
                inputMode="decimal"
                placeholder="0,00"
                value={estimated}
                onChange={(e) => setEstimated(e.target.value)}
              />
            </div>
          </div>

          {podeDesignar && (
            <div>
              <label className="text-xs text-muted" htmlFor="prod-resp">
                Responsável (opcional)
              </label>
              <select
                id="prod-resp"
                className={INPUT_CLASS}
                value={responsibleId}
                onChange={(e) => setResponsibleId(e.target.value)}
              >
                <option value="">Definir depois</option>
                {responsaveis.data?.items.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                    {u.tem_email ? "" : " (sem e-mail)"}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-muted">
                Quem for designado recebe e-mail e o prazo entra na agenda pessoal. Sem
                responsável, o aviso vai para a equipe de figurino.
              </p>
            </div>
          )}

          {criar.isError && !erroCampo("title") && (
            <p className="text-sm text-red">{(criar.error as Error).message}</p>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={fechar}>
            Cancelar
          </Button>
          <Button onClick={salvar} loading={criar.isPending} disabled={!podeSalvar}>
            Abrir pedido
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** Uma linha da fila. O prazo vem primeiro no olhar porque é ele que ordena o trabalho. */
function LinhaPedido({ p }: { p: Producao }) {
  const prazo = prazoInfo(p);
  const estourou = p.estimated_cost != null && p.total_gasto > p.estimated_cost;

  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2">
          <Link
            to={`/figurinos/producao/${p.id}`}
            className="font-medium text-ink hover:text-accent"
          >
            {p.title}
          </Link>
          {p.quantity > 1 && <span className="text-xs text-muted">×{p.quantity}</span>}
          {p.impede_uso && <Badge tone="red">não pode ir</Badge>}
        </div>
        {/* Na manutenção o que orienta é a ficha ("de qual boneco é isto"); na produção, o
            evento. Mostrar os dois em toda linha seria ruído. */}
        {p.figurino_sheet_name && (
          <p className="mt-0.5 truncate text-xs text-muted">{p.figurino_sheet_name}</p>
        )}
        {p.event_title && !p.figurino_sheet_name && (
          <p className="mt-0.5 truncate text-xs text-muted" title={p.event_title}>
            {p.event_title}
          </p>
        )}
      </TableCell>
      <TableCell>
        {p.responsible_name ? (
          <span className="text-sm text-ink">{p.responsible_name}</span>
        ) : (
          <span className="text-sm text-muted">Ninguém ainda</span>
        )}
      </TableCell>
      <TableCell>
        {prazo.tone === "neutral" ? (
          <span className="text-sm text-muted">{prazo.texto}</span>
        ) : (
          <Badge tone={prazo.tone}>{prazo.texto}</Badge>
        )}
      </TableCell>
      <TableCell>
        <div className="text-sm text-ink">
          {p.total_gasto > 0 ? formatBRL(p.total_gasto) : "—"}
          {p.gastos_count > 0 && (
            <span className="ml-1 text-xs text-muted">
              ({p.gastos_count} lanç.)
            </span>
          )}
        </div>
        {p.estimated_cost != null && (
          <p className={`text-xs ${estourou ? "text-red" : "text-muted"}`}>
            previsto {formatBRL(p.estimated_cost)}
          </p>
        )}
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap items-center gap-1">
          <Badge tone={p.kind === "manutencao" ? "accent" : "neutral"}>{p.kind_label}</Badge>
          <Badge tone={PRODUCAO_STATUS_TONES[p.status]}>
            {PRODUCAO_STATUS_LABELS[p.status]}
          </Badge>
        </div>
      </TableCell>
    </TableRow>
  );
}

/**
 * Fila da oficina de figurinos (feature 225).
 *
 * Existe porque o trabalho de produzir figurino não tinha registro: aparecia só depois, em
 * lançamentos soltos de gasto extra — oito linhas para uma peça só, sem nada dizendo que eram o
 * mesmo trabalho, nem quem estava fazendo, nem se ficou pronto.
 */
export function FigurinoProducaoListPage() {
  const { data: user } = useCurrentUser();
  const reduceMotion = useReducedMotion();
  const [searchParams, setSearchParams] = useSearchParams();
  // `?ficha=` é o destino dos avisos de manutenção na lista de figurinos e no elenco do evento:
  // clicar em "não pode ir" tem que cair já filtrado naquele figurino.
  const fichaFiltro = Number(searchParams.get("ficha")) || null;
  const [tipo, setTipo] = useState<ProducaoKind | "">(fichaFiltro ? "manutencao" : "");
  const [filtro, setFiltro] = useState(fichaFiltro ? "" : "abertos");
  const [busca, setBusca] = useState("");
  const [soMeus, setSoMeus] = useState(false);
  const [novoAberto, setNovoAberto] = useState(false);

  const filtros = useMemo(
    () => ({
      abertos: filtro === "abertos",
      status: (filtro === "abertos" ? "" : filtro) as ProducaoStatus | "",
      tipo,
      busca,
      ficha: fichaFiltro,
      responsavel: soMeus ? (user?.id ?? null) : null,
    }),
    [filtro, tipo, busca, fichaFiltro, soMeus, user?.id],
  );
  const { data, isLoading, isError, error } = useProducoes(filtros);

  const itens = data?.items ?? [];
  const flags = data?.flags;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Produção de Figurinos"
        subtitle="O que precisa ser feito, quem está fazendo e quanto já custou"
        actions={
          flags?.can_create ? (
            <Button onClick={() => setNovoAberto(true)}>
              <Plus className="mr-1 h-4 w-4" />
              Novo pedido
            </Button>
          ) : null
        }
      />

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : isError ? (
        <Card className="px-4 py-6 text-sm text-red">
          Não foi possível carregar a fila: {(error as Error).message}
        </Card>
      ) : (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="space-y-4"
        >
          {fichaFiltro && (
            <Card className="flex items-center justify-between gap-3 px-4 py-2">
              <span className="text-sm text-ink">
                Mostrando só o figurino{" "}
                <strong>{itens[0]?.figurino_sheet_name ?? `#${fichaFiltro}`}</strong>.
              </span>
              <Button size="sm" variant="ghost" onClick={() => setSearchParams({})}>
                Ver todos
              </Button>
            </Card>
          )}

          <Resumo itens={itens} />

          {/* Tipo primeiro: produzir uma peça nova e consertar uma que existe são dois
              trabalhos diferentes, com fluxos diferentes. */}
          <div className="flex gap-2 border-b border-line">
            {([["", "Tudo"], ["producao", "Produção"], ["manutencao", "Manutenção"]] as const).map(
              ([valor, rotulo]) => (
                <button
                  key={valor || "tudo"}
                  type="button"
                  onClick={() => setTipo(valor)}
                  className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${
                    tipo === valor
                      ? "border-accent font-medium text-accent"
                      : "border-transparent text-muted hover:text-ink"
                  }`}
                >
                  {rotulo}
                </button>
              ),
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {FILTROS.map((f) => (
              <button
                key={f.key || "tudo"}
                type="button"
                onClick={() => setFiltro(f.key)}
                className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                  filtro === f.key
                    ? "bg-accent-soft font-medium text-accent"
                    : "text-muted hover:bg-surface-2"
                }`}
              >
                {f.label}
              </button>
            ))}
            <label className="ml-auto flex items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={soMeus}
                onChange={(e) => setSoMeus(e.target.checked)}
              />
              Só os meus
            </label>
            <Input
              className="w-full sm:w-56"
              placeholder="Buscar peça…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          </div>

          {itens.length === 0 ? (
            <Card className="flex flex-col items-center gap-2 px-4 py-12 text-center">
              <Shirt className="h-8 w-8 text-muted" />
              <p className="font-medium text-ink">Nada nesta lista</p>
              <p className="max-w-md text-sm text-muted">
                Quando alguém precisar de uma peça para um evento — uma bermuda, um sapato, um
                figurino inteiro — é aqui que o pedido nasce, e é aqui que os gastos dele ficam
                juntos.
              </p>
            </Card>
          ) : (
            <Table>
              <thead>
                <TableRow head>
                  <TableCell as="th">Peça</TableCell>
                  <TableCell as="th">Responsável</TableCell>
                  <TableCell as="th">Prazo</TableCell>
                  <TableCell as="th">Gasto</TableCell>
                  <TableCell as="th">Situação</TableCell>
                </TableRow>
              </thead>
              <tbody>
                {itens.map((p) => (
                  <LinhaPedido key={p.id} p={p} />
                ))}
              </tbody>
            </Table>
          )}
        </motion.div>
      )}

      <NovoPedidoDialog
        open={novoAberto}
        onOpenChange={setNovoAberto}
        podeDesignar={Boolean(flags?.can_execute)}
      />
    </div>
  );
}
