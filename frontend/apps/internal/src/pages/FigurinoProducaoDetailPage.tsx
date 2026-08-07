import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import {
  Camera,
  FileText,
  Link2,
  Receipt,
  Trash2,
  TriangleAlert,
} from "lucide-react";
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
} from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import {
  PRODUCAO_STATUS_LABELS,
  PRODUCAO_STATUS_TONES,
  prazoInfo,
  useAddAnexo,
  useComentar,
  useDesvincularGasto,
  useGastosVinculaveis,
  useMudarStatus,
  useProducao,
  useRemoveAnexo,
  useResponsaveis,
  useUpdateProducao,
  useVincularGasto,
  type Producao,
  type ProducaoAnexo,
  type ProducaoLog,
  type ProducaoStatus,
} from "../lib/figurinoProducao";

const INPUT_CLASS = "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

function dataBR(iso: string | null): string {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

function dataHoraBR(iso: string | null): string {
  if (!iso) return "";
  const [data, hora] = iso.split("T");
  const [ano, mes, dia] = data.split("-");
  return `${dia}/${mes}/${ano} ${(hora ?? "").slice(0, 5)}`;
}

/** Aviso do Google Agenda: o pedido foi salvo, o que falhou foi a integração. */
function AvisoAgenda({ texto, onFechar }: { texto: string; onFechar: () => void }) {
  return (
    <Card className="flex items-start gap-3 border-l-4 border-l-gold px-4 py-3">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-gold-ink" />
      <p className="flex-1 text-sm text-ink">{texto}</p>
      <button type="button" className="text-xs text-muted hover:text-ink" onClick={onFechar}>
        Fechar
      </button>
    </Card>
  );
}

/** Os botões que movem o pedido — o backend diz quais transições existem daqui. */
function AcoesStatus({
  producao,
  transicoes,
  onAviso,
}: {
  producao: Producao;
  transicoes: ProducaoStatus[];
  onAviso: (t: string | undefined) => void;
}) {
  const mudar = useMudarStatus(producao.id);
  const [cancelando, setCancelando] = useState(false);
  const [motivo, setMotivo] = useState("");

  function mover(status: ProducaoStatus) {
    if (status === "cancelado") {
      setCancelando(true);
      return;
    }
    mudar.mutate({ status }, { onSuccess: (r) => onAviso(r.warning) });
  }

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {transicoes.map((s) => (
          <Button
            key={s}
            size="sm"
            variant={s === "cancelado" ? "ghost" : "default"}
            loading={mudar.isPending}
            onClick={() => mover(s)}
          >
            {s === "cancelado" ? "Cancelar pedido" : PRODUCAO_STATUS_LABELS[s]}
          </Button>
        ))}
      </div>
      {mudar.isError && (
        <p className="mt-2 text-sm text-red">{(mudar.error as Error).message}</p>
      )}

      <Dialog open={cancelando} onOpenChange={setCancelando}>
        <DialogContent open={cancelando}>
          <DialogHeader>
            <DialogTitle>Cancelar este pedido</DialogTitle>
            <DialogDescription>
              O pedido continua no sistema, com o histórico e os gastos já lançados.
            </DialogDescription>
          </DialogHeader>
          <label className="text-xs text-muted" htmlFor="motivo-cancel">
            Por quê?
          </label>
          <textarea
            id="motivo-cancel"
            className={`${INPUT_CLASS} h-24 py-2`}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCancelando(false)}>
              Voltar
            </Button>
            <Button
              loading={mudar.isPending}
              disabled={!motivo.trim()}
              onClick={() =>
                mudar.mutate(
                  { status: "cancelado", motivo },
                  {
                    onSuccess: (r) => {
                      onAviso(r.warning);
                      setCancelando(false);
                      setMotivo("");
                    },
                  },
                )
              }
            >
              Cancelar pedido
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Troca de responsável — é ela que dispara o e-mail e o convite na agenda. */
function ResponsavelPicker({
  producao,
  onAviso,
}: {
  producao: Producao;
  onAviso: (t: string | undefined) => void;
}) {
  const responsaveis = useResponsaveis();
  const update = useUpdateProducao(producao.id);
  return (
    <div>
      <label className="text-xs text-muted" htmlFor="resp-picker">
        Responsável
      </label>
      <select
        id="resp-picker"
        className={INPUT_CLASS}
        value={producao.responsible_id ?? ""}
        disabled={update.isPending}
        onChange={(e) =>
          update.mutate(
            { responsible_id: e.target.value ? Number(e.target.value) : null },
            { onSuccess: (r) => onAviso(r.warning) },
          )
        }
      >
        <option value="">Ninguém</option>
        {responsaveis.data?.items.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name}
            {u.tem_email ? "" : " (sem e-mail)"}
          </option>
        ))}
      </select>
      {update.isPending && <p className="mt-1 text-xs text-muted">Salvando…</p>}
    </div>
  );
}

/** Sobe foto de evolução ou orçamento de fornecedor. */
function AnexoUploader({ producaoId }: { producaoId: number }) {
  const add = useAddAnexo(producaoId);
  const fotoRef = useRef<HTMLInputElement>(null);
  const [orcamentoAberto, setOrcamentoAberto] = useState(false);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [fornecedor, setFornecedor] = useState("");
  const [valor, setValor] = useState("");

  return (
    <div className="flex flex-wrap gap-2">
      <input
        ref={fotoRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) add.mutate({ file: f, kind: "foto" });
          e.target.value = "";
        }}
      />
      <Button
        size="sm"
        variant="outline"
        loading={add.isPending}
        onClick={() => fotoRef.current?.click()}
      >
        <Camera className="mr-1 h-4 w-4" />
        Foto do andamento
      </Button>
      <Button size="sm" variant="outline" onClick={() => setOrcamentoAberto(true)}>
        <FileText className="mr-1 h-4 w-4" />
        Anexar orçamento
      </Button>
      {add.isError && <p className="w-full text-sm text-red">{(add.error as Error).message}</p>}

      <Dialog open={orcamentoAberto} onOpenChange={setOrcamentoAberto}>
        <DialogContent open={orcamentoAberto}>
          <DialogHeader>
            <DialogTitle>Orçamento de fornecedor</DialogTitle>
            <DialogDescription>
              Guarde as propostas aqui para comparar antes de decidir. Aceita foto ou PDF.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted" htmlFor="orc-file">
                Arquivo
              </label>
              <input
                id="orc-file"
                type="file"
                accept="image/*,.pdf"
                className={`${INPUT_CLASS} py-2`}
                onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted" htmlFor="orc-forn">
                  Fornecedor
                </label>
                <Input
                  id="orc-forn"
                  value={fornecedor}
                  placeholder="Siomar"
                  onChange={(e) => setFornecedor(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-muted" htmlFor="orc-valor">
                  Valor
                </label>
                <Input
                  id="orc-valor"
                  inputMode="decimal"
                  placeholder="0,00"
                  value={valor}
                  onChange={(e) => setValor(e.target.value)}
                />
              </div>
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOrcamentoAberto(false)}>
              Cancelar
            </Button>
            <Button
              loading={add.isPending}
              disabled={!arquivo}
              onClick={() =>
                arquivo &&
                add.mutate(
                  {
                    file: arquivo,
                    kind: "orcamento",
                    supplier_name: fornecedor,
                    amount: valor,
                  },
                  {
                    onSuccess: () => {
                      setOrcamentoAberto(false);
                      setArquivo(null);
                      setFornecedor("");
                      setValor("");
                    },
                  },
                )
              }
            >
              Anexar
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Orcamentos({
  producaoId,
  anexos,
  podeEditar,
}: {
  producaoId: number;
  anexos: ProducaoAnexo[];
  podeEditar: boolean;
}) {
  const remover = useRemoveAnexo(producaoId);
  const orcamentos = anexos.filter((a) => a.kind === "orcamento");
  if (!orcamentos.length) return null;

  // O menor valor é a informação que a tela existe para dar — comparar propostas.
  const menor = Math.min(...orcamentos.map((o) => o.amount ?? Infinity));

  return (
    <Card className="px-4 py-3">
      <h3 className="mb-2 text-sm font-semibold text-ink">Orçamentos</h3>
      <ul className="space-y-1">
        {orcamentos.map((o) => (
          <li key={o.id} className="flex items-center gap-2 text-sm">
            <a
              href={assetUrl(o.url)}
              target="_blank"
              rel="noreferrer"
              className="flex-1 truncate text-ink hover:text-accent"
            >
              {o.supplier_name || o.original_name || "Orçamento"}
            </a>
            {o.amount != null && (
              <span
                className={
                  o.amount === menor ? "font-semibold text-green" : "tabular-nums text-muted"
                }
              >
                {formatBRL(o.amount)}
              </span>
            )}
            {podeEditar && (
              <button
                type="button"
                aria-label="Remover orçamento"
                className="text-muted hover:text-red"
                onClick={() => remover.mutate(o.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** Gastos extras vinculados — é isto que responde "quanto custou de verdade". */
function Gastos({
  producao,
  podeEditar,
}: {
  producao: Producao;
  podeEditar: boolean;
}) {
  const [aberto, setAberto] = useState(false);
  const vincular = useVincularGasto(producao.id);
  const desvincular = useDesvincularGasto(producao.id);
  const disponiveis = useGastosVinculaveis(aberto ? producao.id : null);
  const gastos = producao.gastos ?? [];
  const estourou =
    producao.estimated_cost != null && producao.total_gasto > producao.estimated_cost;

  return (
    <Card className="px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">Gastos</h3>
        {podeEditar && (
          <Button size="sm" variant="ghost" onClick={() => setAberto(true)}>
            <Link2 className="mr-1 h-4 w-4" />
            Vincular
          </Button>
        )}
      </div>

      {gastos.length === 0 ? (
        <p className="text-sm text-muted">
          Nenhum gasto vinculado ainda. Vincule os lançamentos de Gastos Extras que pertencem a
          esta peça — inclusive os antigos.
        </p>
      ) : (
        <ul className="space-y-1">
          {gastos.map((g) => (
            <li key={g.id} className="flex items-center gap-2 text-sm">
              <span className="w-20 shrink-0 text-xs text-muted">{dataBR(g.expense_date)}</span>
              <span className="flex-1 truncate text-ink">{g.description}</span>
              {g.status !== "aprovado" && (
                <Badge tone={g.status === "rejeitado" ? "red" : "neutral"}>{g.status}</Badge>
              )}
              <span className="tabular-nums text-ink">{formatBRL(g.amount)}</span>
              {podeEditar && (
                <button
                  type="button"
                  aria-label="Desvincular gasto"
                  className="text-muted hover:text-red"
                  onClick={() => desvincular.mutate(g.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex items-baseline justify-between border-t border-line pt-2">
        <span className="text-xs text-muted">
          Total aprovado
          {producao.estimated_cost != null && ` · previsto ${formatBRL(producao.estimated_cost)}`}
        </span>
        <span className={`text-lg font-semibold ${estourou ? "text-red" : "text-ink"}`}>
          {formatBRL(producao.total_gasto)}
        </span>
      </div>
      {estourou && (
        <p className="mt-1 text-xs text-red">
          Passou {formatBRL(producao.total_gasto - (producao.estimated_cost ?? 0))} do previsto.
        </p>
      )}

      <Dialog open={aberto} onOpenChange={setAberto}>
        <DialogContent open={aberto} className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Vincular gasto a esta peça</DialogTitle>
            <DialogDescription>
              Gastos de figurino e do mesmo evento. Vincular não recria nada: o lançamento
              continua o mesmo, com data, comprovante e aprovação.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-96 overflow-y-auto">
            {disponiveis.isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <ul className="space-y-1">
                {disponiveis.data?.items.map((g) => (
                  <li
                    key={g.id}
                    className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-surface-2"
                  >
                    <span className="w-20 shrink-0 text-xs text-muted">
                      {dataBR(g.expense_date)}
                    </span>
                    <span className="flex-1 truncate text-ink" title={g.event_title ?? ""}>
                      {g.description}
                    </span>
                    <span className="tabular-nums text-muted">{formatBRL(g.amount)}</span>
                    {g.ja_vinculado ? (
                      <Badge tone="green">vinculado</Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={vincular.isPending}
                        onClick={() => vincular.mutate(g.id)}
                      >
                        Vincular
                      </Button>
                    )}
                  </li>
                ))}
                {disponiveis.data?.items.length === 0 && (
                  <p className="px-2 py-4 text-sm text-muted">
                    Nenhum gasto disponível para vincular.
                  </p>
                )}
              </ul>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

/** O "mini histórico de evolução": o que aconteceu, quem fez, e a foto de quando fez. */
function Historico({
  producaoId,
  logs,
}: {
  producaoId: number;
  logs: ProducaoLog[];
}) {
  const comentar = useComentar(producaoId);
  const [texto, setTexto] = useState("");

  return (
    <Card className="px-4 py-3">
      <h3 className="mb-2 text-sm font-semibold text-ink">Histórico</h3>

      <div className="mb-3 flex gap-2">
        <Input
          placeholder="Escrever uma nota…"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && texto.trim()) {
              comentar.mutate(texto, { onSuccess: () => setTexto("") });
            }
          }}
        />
        <Button
          loading={comentar.isPending}
          disabled={!texto.trim()}
          onClick={() => comentar.mutate(texto, { onSuccess: () => setTexto("") })}
        >
          Anotar
        </Button>
      </div>

      <ol className="space-y-3">
        {logs.map((log) => (
          <li key={log.id} className="border-l-2 border-line pl-3">
            <p className="text-sm text-ink">{log.message}</p>
            {log.photo_url && (
              <a href={assetUrl(log.photo_url)} target="_blank" rel="noreferrer">
                <img
                  src={assetUrl(log.photo_url)}
                  alt={log.message}
                  loading="lazy"
                  className="mt-2 max-h-56 rounded-md border border-line object-cover"
                />
              </a>
            )}
            <p className="mt-1 text-xs text-muted">
              {log.actor_name} · {dataHoraBR(log.created_at)}
            </p>
          </li>
        ))}
        {logs.length === 0 && <p className="text-sm text-muted">Nada registrado ainda.</p>}
      </ol>
    </Card>
  );
}

/**
 * Detalhe de um pedido de produção de figurino (feature 225).
 *
 * Junta num lugar só o que hoje está espalhado: o que precisa ser feito, quem faz, até quando,
 * quanto se esperava gastar, quanto se gastou de verdade, as fotos da evolução, os orçamentos
 * dos fornecedores e o histórico.
 */
export function FigurinoProducaoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const [aviso, setAviso] = useState<string | undefined>();
  const { data, isLoading, isError, error } = useProducao(id ? Number(id) : null);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <Card className="px-4 py-6">
        <p className="text-sm text-red">
          Não foi possível abrir o pedido: {(error as Error)?.message ?? "não encontrado"}
        </p>
        <Button className="mt-3" variant="outline" onClick={() => navigate("/figurinos/producao")}>
          Voltar para a fila
        </Button>
      </Card>
    );
  }

  const p = data.producao;
  const prazo = prazoInfo(p);
  const podeEditar = data.flags.can_execute;
  const fotos = (p.anexos ?? []).filter((a) => a.kind === "foto");

  return (
    <div className="space-y-4">
      <PageHeader
        title={p.title}
        subtitle={
          p.event_title ? (
            <span>
              para <span className="text-ink">{p.event_title}</span>
            </span>
          ) : (
            "sem evento vinculado"
          )
        }
        breadcrumbs={[
          { label: "Produção de Figurinos", href: "/figurinos/producao" },
          { label: p.title },
        ]}
        renderCrumb={(crumb, className) =>
          crumb.href ? (
            <Link to={crumb.href} className={className}>
              {crumb.label}
            </Link>
          ) : (
            <span className={className}>{crumb.label}</span>
          )
        }
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={p.kind === "manutencao" ? "accent" : "neutral"}>{p.kind_label}</Badge>
            <Badge tone={PRODUCAO_STATUS_TONES[p.status]}>{p.status_label}</Badge>
          </div>
        }
      />

      {/* O aviso que justifica o módulo existir: enquanto isto estiver aberto, este boneco não
          pode ser escalado. Aparece antes de qualquer outra coisa da tela. */}
      {p.impede_uso && (
        <Card className="flex items-start gap-3 border-l-4 border-l-red px-4 py-3">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-red" />
          <p className="flex-1 text-sm text-ink">
            <span className="font-semibold text-red">Este figurino não pode ir para evento</span>{" "}
            até o conserto. O aviso aparece na ficha
            {p.figurino_sheet_name ? ` de ${p.figurino_sheet_name}` : ""} e no elenco de quem
            escalar esse personagem.
          </p>
        </Card>
      )}

      {aviso && <AvisoAgenda texto={aviso} onFechar={() => setAviso(undefined)} />}

      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="grid gap-4 lg:grid-cols-[1fr_340px]"
      >
        <div className="space-y-4">
          {p.description && (
            <Card className="px-4 py-3">
              <h3 className="mb-1 text-sm font-semibold text-ink">
                {p.kind === "manutencao"
                  ? "O que precisa ser resolvido"
                  : "O que precisa ser feito"}
              </h3>
              <p className="whitespace-pre-wrap text-sm text-ink">{p.description}</p>
            </Card>
          )}

          {p.status === "cancelado" && p.cancellation_reason && (
            <Card className="border-l-4 border-l-red px-4 py-3">
              <p className="text-sm text-ink">
                <span className="font-semibold">Cancelado:</span> {p.cancellation_reason}
              </p>
            </Card>
          )}

          {fotos.length > 0 && (
            <Card className="px-4 py-3">
              <h3 className="mb-2 text-sm font-semibold text-ink">Fotos</h3>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                {fotos.map((f) => (
                  <a key={f.id} href={assetUrl(f.url)} target="_blank" rel="noreferrer">
                    <img
                      src={assetUrl(f.url)}
                      alt={f.caption ?? "Foto do andamento"}
                      loading="lazy"
                      className="aspect-square w-full rounded-md border border-line object-cover"
                    />
                  </a>
                ))}
              </div>
            </Card>
          )}

          {/* Manutenção sem custo previsto e sem gasto lançado não mostra o painel de dinheiro:
              a maior parte é trabalho manual, e um "R$ 0,00" grande sugeriria que falta lançar
              alguma coisa. Se aparecer gasto ou previsão, o painel volta sozinho. */}
          {(p.kind !== "manutencao" || p.total_gasto > 0 || p.estimated_cost != null) && (
            <Gastos producao={p} podeEditar={podeEditar} />
          )}
          <Historico producaoId={p.id} logs={p.logs ?? []} />
        </div>

        <div className="space-y-4">
          <Card className="space-y-3 px-4 py-3">
            {podeEditar ? (
              <AcoesStatus producao={p} transicoes={data.transicoes} onAviso={setAviso} />
            ) : (
              <p className="text-sm text-muted">
                Só a equipe de figurino move este pedido.
              </p>
            )}

            <div className="space-y-2 border-t border-line pt-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted">Prazo</span>
                {prazo.tone === "neutral" ? (
                  <span className="text-ink">{prazo.texto}</span>
                ) : (
                  <Badge tone={prazo.tone}>{prazo.texto}</Badge>
                )}
              </div>
              {p.quantity > 1 && (
                <div className="flex justify-between">
                  <span className="text-muted">Quantidade</span>
                  <span className="text-ink">{p.quantity}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted">Pedido por</span>
                <span className="text-ink">{p.requested_by ?? "—"}</span>
              </div>
              {p.approved_by && (
                <div className="flex justify-between">
                  <span className="text-muted">Aprovado por</span>
                  <span className="text-ink">{p.approved_by}</span>
                </div>
              )}
              {p.figurino_sheet_name && (
                <div className="flex justify-between">
                  <span className="text-muted">Figurino</span>
                  <span className="text-ink">{p.figurino_sheet_name}</span>
                </div>
              )}
              {p.severity_label && (
                <div className="flex items-center justify-between">
                  <span className="text-muted">Situação da peça</span>
                  <Badge tone={p.severity === "impede_uso" ? "red" : "gold"}>
                    {p.severity_label}
                  </Badge>
                </div>
              )}
              {p.event_id && (
                <div className="flex justify-between">
                  <span className="text-muted">Evento</span>
                  <Link to={`/events/${p.event_id}`} className="text-accent hover:underline">
                    abrir
                  </Link>
                </div>
              )}
            </div>

            {podeEditar && (
              <div className="border-t border-line pt-3">
                <ResponsavelPicker producao={p} onAviso={setAviso} />
                {p.google_event_id && (
                  <p className="mt-1 text-xs text-muted">
                    O prazo está na agenda, com convite para quem é responsável.
                  </p>
                )}
              </div>
            )}
          </Card>

          {podeEditar && (
            <Card className="px-4 py-3">
              <h3 className="mb-2 text-sm font-semibold text-ink">Anexar</h3>
              <AnexoUploader producaoId={p.id} />
            </Card>
          )}

          <Orcamentos producaoId={p.id} anexos={p.anexos ?? []} podeEditar={podeEditar} />

          <Card className="px-4 py-3">
            <Link
              to="/gastos"
              className="flex items-center gap-2 text-sm text-accent hover:underline"
            >
              <Receipt className="h-4 w-4" />
              Lançar um gasto novo
            </Link>
            <p className="mt-1 text-xs text-muted">
              Depois de lançar, volte aqui e use “Vincular”.
            </p>
          </Card>
        </div>
      </motion.div>
    </div>
  );
}
