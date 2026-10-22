import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Combobox, ConfirmDialog, formatShortDate } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { useAgendaSearch } from "../../lib/agenda";
import { mensagemDaApi } from "../../lib/formulariosAdmin";
import {
  eRepasse,
  useConfirmarPix,
  useDescartarPix,
  useDesfazerPix,
  useNaoEVendaPix,
  type PixRecebido,
  type SugestaoRepasse,
  type SugestaoVenda,
} from "../../lib/pix";

function dinheiro(valor: string | null | undefined): string {
  return valor == null ? "—" : formatBRL(Number(valor));
}

function quando(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/** Os selos do porquê ("valor = saldo", "nome bate", "já pagou antes"). */
function Motivos({ motivos }: { motivos: string[] }) {
  return (
    <span className="flex flex-wrap gap-1">
      {motivos.map((m) => (
        <Badge key={m} tone={m.startsWith("valor") || m.startsWith("comprovante") ? "green" : "blue"}>
          {m}
        </Badge>
      ))}
    </span>
  );
}

/** Uma venda sugerida com "É esta" e "Não é esta". */
function LinhaSugestao({ pix, sugestao }: { pix: PixRecebido; sugestao: SugestaoVenda }) {
  const confirmar = useConfirmarPix();
  const descartar = useDescartarPix();
  const [descartando, setDescartando] = useState(false);
  return (
    <li className="flex flex-wrap items-center gap-2 py-2">
      <div className="min-w-0 flex-1 text-sm">
        <Link to={`/events/${sugestao.event_id}?aba=comercial`} className="font-medium text-blue underline">
          {sugestao.titulo}
        </Link>
        <span className="text-muted">
          {" "}
          · {formatShortDate(sugestao.data)}
          {sugestao.cliente && ` · ${sugestao.cliente}`}
          {sugestao.vendedor && ` · vendedor: ${sugestao.vendedor}`}
          {sugestao.saldo && ` · falta ${dinheiro(sugestao.saldo)}`}
        </span>
        <div className="mt-1">
          <Motivos motivos={sugestao.motivos} />
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <Button
          size="sm"
          loading={confirmar.isPending}
          onClick={() => confirmar.mutate({ pixId: pix.id, eventIds: [sugestao.event_id] })}
        >
          É esta
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setDescartando(true)}>
          Não é esta
        </Button>
      </div>
      {confirmar.isError && (
        <p role="alert" className="w-full text-xs text-red">
          {mensagemDaApi(confirmar.error, "Não foi possível ligar. Tente novamente.")}
        </p>
      )}
      <ConfirmDialog
        open={descartando}
        title="Não é esta venda?"
        description="A venda sai das sugestões deste PIX. Ainda dá para escolher outra venda."
        confirmLabel="Não é esta"
        pending={descartar.isPending}
        error={descartar.isError ? mensagemDaApi(descartar.error, "Não foi possível descartar.") : null}
        onConfirm={() =>
          descartar.mutate(
            { pixId: pix.id, eventId: sugestao.event_id },
            { onSuccess: () => setDescartando(false) },
          )
        }
        onOpenChange={(aberto) => {
          if (!aberto) {
            setDescartando(false);
            descartar.reset();
          }
        }}
      />
    </li>
  );
}

/** Repasse da InfinitePay: marcar 1–3 vendas no cartão; a soma e a taxa aparecem. */
function SugestoesRepasse({ pix, sugestoes }: { pix: PixRecebido; sugestoes: SugestaoRepasse[] }) {
  const confirmar = useConfirmarPix();
  return (
    <ul className="divide-y divide-line">
      {sugestoes.map((s) => (
        <li key={s.event_ids.join("-")} className="flex flex-wrap items-center gap-2 py-2">
          <div className="min-w-0 flex-1 text-sm">
            {s.vendas.map((v) => (
              <div key={v.event_id}>
                <Link to={`/events/${v.event_id}?aba=comercial`} className="text-blue underline">
                  {v.titulo}
                </Link>
                <span className="text-muted">
                  {" "}
                  · {formatShortDate(v.data)}
                  {v.cliente && ` · ${v.cliente}`}
                </span>
              </div>
            ))}
            <div className="mt-1 text-xs text-muted tabular-nums">
              Cobrado {dinheiro(s.soma)} · taxa {dinheiro(s.taxa)}
            </div>
          </div>
          <Button
            size="sm"
            loading={confirmar.isPending}
            onClick={() => confirmar.mutate({ pixId: pix.id, eventIds: s.event_ids })}
          >
            {s.event_ids.length > 1 ? "São estas" : "É esta"}
          </Button>
        </li>
      ))}
      {confirmar.isError && (
        <p role="alert" className="py-1 text-xs text-red">
          {mensagemDaApi(confirmar.error, "Não foi possível ligar. Tente novamente.")}
        </p>
      )}
    </ul>
  );
}

/** "Outra venda…": busca qualquer venda aberta (o servidor confere se ela ainda deve). */
function OutraVenda({ pix }: { pix: PixRecebido }) {
  const [busca, setBusca] = useState("");
  const resultado = useAgendaSearch(busca);
  const confirmar = useConfirmarPix();
  const opcoes = useMemo(
    () =>
      (resultado.data?.items ?? []).map((ev) => ({
        value: String(ev.id),
        label: ev.start_at ? `${ev.title} — ${formatShortDate(ev.start_at)}` : ev.title,
        description: ev.client_name ?? undefined,
      })),
    [resultado.data],
  );
  return (
    <div className="mt-2">
      <Combobox
        options={opcoes}
        value={null}
        onChange={(valor) =>
          valor !== null && confirmar.mutate({ pixId: pix.id, eventIds: [Number(valor)] })
        }
        onQueryChange={setBusca}
        loading={resultado.isFetching || confirmar.isPending}
        hintMessage="Digite ao menos 2 letras do evento, da cliente ou do telefone"
        placeholder="Outra venda… (buscar evento)"
        aria-label="Buscar outra venda"
      />
      {confirmar.isError && (
        <p role="alert" className="mt-1 text-xs text-red">
          {mensagemDaApi(confirmar.error, "Não foi possível ligar a essa venda.")}
        </p>
      )}
    </div>
  );
}

/**
 * Um PIX da fila "É esta?" (feature 318) — mesmo vocabulário do padrão "liga sozinho / pergunta
 * quando há dúvida" da 298 (formulário → evento): "É esta", "Não é esta", "Outra venda…" e
 * "Não é de venda".
 */
export function CartaoPixParaConferir({ pix }: { pix: PixRecebido }) {
  const reduceMotion = useReducedMotion();
  const naoEVenda = useNaoEVendaPix();
  const [naoE, setNaoE] = useState(false);
  const [outra, setOutra] = useState(false);
  const repasse = pix.tipo_sugestao === "repasse_infinitepay";
  const vendas = pix.sugestoes.filter((s): s is SugestaoVenda => !eRepasse(s, pix));
  const repasses = pix.sugestoes.filter((s): s is SugestaoRepasse => eRepasse(s, pix));

  return (
    <motion.li
      layout={!reduceMotion}
      initial={reduceMotion ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="rounded-lg border border-line bg-panel p-4"
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-lg font-semibold tabular-nums text-ink">{dinheiro(pix.valor)}</span>
        <span className="text-sm text-ink">{repasse ? "Repasse da InfinitePay (Prime Dreams)" : pix.pagador ?? "—"}</span>
        <span className="text-sm text-muted">
          {pix.conta ?? "conta não cadastrada"} · {quando(pix.recebido_em)}
        </span>
        {!pix.autenticado && <Badge tone="red">e-mail não autenticado pelo Inter</Badge>}
      </div>
      <p className="mt-1 text-sm text-muted">
        {repasse ? "Quais vendas no cartão este repasse paga?" : "É de qual venda?"}
        {pix.motivo && ` (${pix.motivo})`}
      </p>

      {repasse ? (
        <SugestoesRepasse pix={pix} sugestoes={repasses} />
      ) : (
        <ul className="divide-y divide-line">
          {vendas.map((s) => (
            <LinhaSugestao key={s.event_id} pix={pix} sugestao={s} />
          ))}
        </ul>
      )}

      <div className="mt-2 flex flex-wrap gap-2">
        {!repasse && (
          <Button size="sm" variant="outline" onClick={() => setOutra((v) => !v)}>
            Outra venda…
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={() => setNaoE(true)}>
          Não é de venda
        </Button>
      </div>
      {outra && !repasse && <OutraVenda pix={pix} />}

      <ConfirmDialog
        open={naoE}
        title="Não é de venda?"
        description="O PIX sai da fila e não volta. Use para transferências, aportes, empréstimos e devoluções."
        confirmLabel="Não é de venda"
        pending={naoEVenda.isPending}
        error={naoEVenda.isError ? mensagemDaApi(naoEVenda.error, "Não foi possível tirar da fila.") : null}
        onConfirm={() => naoEVenda.mutate({ pixId: pix.id }, { onSuccess: () => setNaoE(false) })}
        onOpenChange={(aberto) => {
          if (!aberto) {
            setNaoE(false);
            naoEVenda.reset();
          }
        }}
      />
    </motion.li>
  );
}

/** Um PIX já ligado (aba "Ligados"), com "Desfazer" para Financeiro/Superadmin. */
export function CartaoPixLigado({ pix, podeDesfazer }: { pix: PixRecebido; podeDesfazer: boolean }) {
  const desfazer = useDesfazerPix();
  const [confirmando, setConfirmando] = useState(false);
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 text-sm">
      <span className="w-28 shrink-0 font-medium tabular-nums text-ink">{dinheiro(pix.valor)}</span>
      <span className="min-w-0 flex-1">
        <span className="text-ink">{pix.pagador ?? "—"}</span>
        <span className="text-muted">
          {" "}
          · {pix.conta ?? "conta não cadastrada"} · {quando(pix.recebido_em)}
        </span>
        {pix.pagamento && (
          <>
            {" → "}
            <Link to={`/events/${pix.pagamento.event_id}?aba=comercial`} className="text-blue underline">
              {pix.pagamento.titulo ?? "venda"}
            </Link>
          </>
        )}
      </span>
      <Badge tone={pix.estado === "ligado_auto" ? "green" : "blue"}>
        {pix.estado === "ligado_auto" ? "automático" : `confirmado por ${pix.decidido_por ?? "—"}`}
      </Badge>
      {podeDesfazer && (
        <Button size="sm" variant="ghost" onClick={() => setConfirmando(true)}>
          Desfazer
        </Button>
      )}
      <ConfirmDialog
        open={confirmando}
        title="Desfazer a ligação?"
        description="O pagamento criado pelo PIX sai da venda (se já tiver comprovante anexado, fica como pagamento manual) e o PIX volta para conferir."
        confirmLabel="Desfazer"
        pending={desfazer.isPending}
        error={desfazer.isError ? mensagemDaApi(desfazer.error, "Não foi possível desfazer.") : null}
        onConfirm={() =>
          desfazer.mutate(
            { pixId: pix.id, eventId: pix.pagamento?.event_id },
            { onSuccess: () => setConfirmando(false) },
          )
        }
        onOpenChange={(aberto) => {
          if (!aberto) {
            setConfirmando(false);
            desfazer.reset();
          }
        }}
      />
    </li>
  );
}
