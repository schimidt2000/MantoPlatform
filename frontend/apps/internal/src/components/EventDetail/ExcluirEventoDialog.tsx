import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Skeleton,
} from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { formatBRL, MoneyInput } from "@manto/money";
import {
  codigoDaRecusa,
  useCancelarEvento,
  useDeleteEvent,
  useImpactoExclusao,
  usePreviaCancelamento,
  type AlcanceCancelamento,
  type CancelarEventoInput,
  type EfeitoCancelamento,
  type ImpactoExclusao,
} from "../../lib/eventOps";
import { CancelamentoBvBloco, type BvEntrada } from "./CancelamentoBvBloco";
import { CancelamentoDevolucaoBloco, type DevolucaoState } from "./CancelamentoDevolucaoBloco";
import { CancelamentoDiasBloco } from "./CancelamentoDiasBloco";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

/** `AAAA-MM-DD` / `AAAA-MM` → `DD/MM` / `MM/AAAA`, pela string (sem `new Date`). */
function dataCurta(iso: string | null | undefined): string {
  if (!iso) return "";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return dia ? `${dia}/${mes}` : `${mes}/${ano}`;
}

const DEVOLUCAO_VAZIA: DevolucaoState = { modo: null, valor: 0, nome: "", pix: "", observacao: "" };

/** Painel que explica o que está preso no evento — é o que decide entre excluir e cancelar. */
function ResumoImpacto({ impacto }: { impacto: ImpactoExclusao }) {
  const comissoesPagas = impacto.comissoes.filter((c) => c.status === "pago" || c.status === "no_banco");
  const linhas: string[] = [];
  if (impacto.sale_value > 0) linhas.push(`Venda de ${brl(impacto.sale_value)}`);
  const pago = impacto.pago ?? impacto.total_recebido;
  if (pago > 0) linhas.push(`${brl(pago)} já recebidos da cliente`);
  if (impacto.tem_contrato) linhas.push("Contrato anexado");
  if (impacto.elenco.length > 0) linhas.push(`${impacto.elenco.length} escalação(ões) com artista`);
  if (comissoesPagas.length > 0)
    linhas.push(`Comissão já paga a ${comissoesPagas.map((c) => c.seller_name ?? "—").join(", ")}`);
  if (impacto.gastos_vinculados.length > 0)
    linhas.push(`${impacto.gastos_vinculados.length} gasto(s) extra(s) vinculado(s)`);

  if (impacto.acao === "excluir") {
    return (
      <div className="rounded-md border border-line bg-surface-2 p-3 text-sm text-ink">
        <p className="font-semibold">Este evento está vazio — será excluído de vez.</p>
        <p className="mt-1 text-muted">
          Sem venda, sem pagamento recebido, sem contrato e sem ninguém escalado. Sai do sistema
          e do Google Agenda, sem deixar registro.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="note">
      <p className="font-semibold text-gold-ink">Este evento será cancelado, não excluído.</p>
      {linhas.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink">
          {linhas.map((linha) => (
            <li key={linha}>{linha}</li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-ink">
        O registro fica (é a ele que a devolução se refere), mas o evento sai da agenda e das
        listas. A comissão e o BV passam a acompanhar o que a Manto reteve.
      </p>
    </div>
  );
}

/** "Efeito na comissão": o que o servidor calculou para a devolução escolhida (FR-011). */
function EfeitoNaComissao({ efeito, carregando }: { efeito?: EfeitoCancelamento; carregando: boolean }) {
  if (!efeito) {
    return carregando ? <Skeleton className="h-16 w-full" /> : null;
  }
  // Feature 306, H5: no corte ninguém fica com retido — a venda do grupo diminui, e a comissão e o
  // BV dela acompanham.
  if (efeito.retido == null) {
    return (
      <div className="rounded-md border border-line bg-surface-2 p-3 text-sm" aria-live="polite">
        <p className="mb-1 text-xs font-semibold uppercase text-muted">Efeito no grupo</p>
        <p className="text-ink">
          Comissão da venda do grupo passa a <strong>{brl(efeito.comissao_cheia)}</strong>
          {efeito.ajuste != null && (
            <>
              {" "}
              — {efeito.ajuste < 0 ? "desconto de" : "acréscimo de"} {brl(Math.abs(efeito.ajuste))}
              {efeito.repasse_em ? ` no repasse de ${dataCurta(efeito.repasse_em)}` : ""}
            </>
          )}
          .
        </p>
        {efeito.bv_retido > 0 && <p className="text-ink">BV a pagar do grupo: {brl(efeito.bv_retido)}.</p>}
      </div>
    );
  }
  return (
    <div className="rounded-md border border-line bg-surface-2 p-3 text-sm" aria-live="polite">
      <p className="mb-1 text-xs font-semibold uppercase text-muted">Efeito do cancelamento</p>
      <p className="text-ink">
        A Manto retém <strong>{brl(efeito.retido ?? 0)}</strong>.
      </p>
      {efeito.comissao_cheia > 0 && (
        <p className="text-ink">
          Comissão: {brl(efeito.comissao_cheia)} cheia → {brl(efeito.comissao_retido ?? 0)} do retido
          {efeito.ajuste != null && (
            <>
              {" "}
              — {efeito.ajuste < 0 ? "desconto de" : "acréscimo de"} {brl(Math.abs(efeito.ajuste))}
              {efeito.repasse_em ? ` no repasse de ${dataCurta(efeito.repasse_em)}` : ""}
            </>
          )}
          .
        </p>
      )}
      {efeito.bv_retido > 0 && <p className="text-ink">BV a pagar: {brl(efeito.bv_retido)}.</p>}
    </div>
  );
}

export interface ExcluirEventoDialogProps {
  eventId: number;
  eventTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Diálogo único de excluir/cancelar (features 224 e 306). O servidor decide qual das duas ações
 * vale (`impacto.acao`) e a tela explica o porquê antes de qualquer confirmação.
 *
 * Cancelar (306, FR-023): começa sem modo de devolução marcado; a prévia vem do servidor (a mesma
 * conta da execução); Cancelar fica desabilitado até tudo estar informado; cada recusa aparece no
 * campo certo (`fields`) ou pela frase do `codigo`. Nenhuma conta de dinheiro no navegador.
 */
export function ExcluirEventoDialog({ eventId, eventTitle, open, onOpenChange }: ExcluirEventoDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const impacto = useImpactoExclusao(eventId, open);
  const excluir = useDeleteEvent(eventId);
  const cancelar = useCancelarEvento(eventId);

  const [motivo, setMotivo] = useState("");
  const [devolucao, setDevolucao] = useState<DevolucaoState>(DEVOLUCAO_VAZIA);
  const [imposto, setImposto] = useState(0);
  const [impostoInformado, setImpostoInformado] = useState(false);
  const [bvs, setBvs] = useState<Record<number, BvEntrada>>({});
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erro, setErro] = useState("");
  const [alcance, setAlcance] = useState<AlcanceCancelamento | null>(null);
  const [vendaNova, setVendaNova] = useState(0);
  // Até a pessoa digitar, o "Novo valor da venda" acompanha a venda do grupo que o servidor manda
  // (o impacto da abertura anterior fica no cache e é rebuscado ao abrir).
  const [vendaEditada, setVendaEditada] = useState(false);
  const sugeriu = useRef(false);

  const dados = impacto.data;

  // O nome é sugerido uma vez por abertura; fechar limpa tudo (FR-023).
  useEffect(() => {
    if (open && dados && !sugeriu.current) {
      sugeriu.current = true;
      setDevolucao((d) => ({ ...d, nome: dados.cliente_nome ?? "" }));
    }
  }, [open, dados]);
  useEffect(() => {
    if (open && dados && !vendaEditada) setVendaNova(dados.venda_do_grupo ?? 0);
  }, [open, dados, vendaEditada]);
  useEffect(() => {
    if (!open) {
      sugeriu.current = false;
      setMotivo("");
      setDevolucao(DEVOLUCAO_VAZIA);
      setImposto(0);
      setImpostoInformado(false);
      setBvs({});
      setErros({});
      setErro("");
      setAlcance(null);
      setVendaNova(0);
      setVendaEditada(false);
    }
  }, [open]);

  const cancelando = dados?.acao === "cancelar";
  const regime = dados?.regime;
  const venda = regime === "venda";
  const virtual = regime === "virtual";
  const atualizando = cancelando && regime === undefined;
  // Feature 306, H5: o grupo. Um dia do grupo (`dia`) é o corte; o 1º dia com outros dias vivos
  // escolhe entre todos e só ele (a venda passa ao dia vivo mais cedo, e é corte também).
  const grupo = dados?.grupo ?? null;
  const ehDia = regime === "dia";
  const outrosVivos = Boolean(grupo && !ehDia && grupo.dias.some((d) => d.id !== eventId && !d.cancelado));
  const corta = ehDia || (outrosVivos && alcance === "so_este_dia");
  const comDevolucao = venda || ehDia;
  const vendaDoGrupo = dados?.venda_do_grupo ?? dados?.sale_value ?? 0;
  const vendaNovaValida = vendaNova > 0 && vendaNova <= vendaDoGrupo;
  const pago = dados?.pago ?? dados?.total_recebido ?? 0;
  const maxDevolucao = dados?.max_devolucao ?? 0;
  const devolve =
    devolucao.modo === "tudo"
      ? maxDevolucao
      : devolucao.modo === "parte"
        ? devolucao.valor
        : devolucao.modo === "nada"
          ? 0
          : null;
  const previa = usePreviaCancelamento(
    eventId,
    devolve,
    open && Boolean(cancelando) && comDevolucao && devolve != null && (!outrosVivos || alcance !== null) &&
      (!corta || vendaNovaValida),
    { vendaNova: corta ? vendaNova : null, alcance },
  );
  const efeito = devolve != null ? previa.data?.efeito : undefined;
  // A prévia que esbarra no estado de agora (o dia já foi cancelado, ou ficou sem outro dia vivo)
  // rebusca o impacto, como a recusa do POST faz.
  const codigoDaPrevia = codigoDaRecusa(previa.error);
  useEffect(() => {
    if (codigoDaPrevia === "ja_cancelado" || codigoDaPrevia === "sem_outro_dia_vivo") {
      setAlcance(null);
      void impacto.refetch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [codigoDaPrevia]);
  const proporcional = useMemo(
    () => new Map((efeito?.bvs ?? []).map((b) => [b.acrescimo_id, b.bv_retido])),
    [efeito],
  );

  const pendencia = useMemo<string | null>(() => {
    if (!dados || !cancelando) return null;
    if (atualizando) return "O sistema está atualizando — tente em um minuto.";
    if (!motivo.trim()) return "Explique o motivo do cancelamento.";
    if (outrosVivos && alcance === null) return "Escolha se cancela todos os dias ou só este.";
    if (!comDevolucao) return null;
    if (corta && !vendaNovaValida) return "Informe o novo valor da venda do grupo (até o de hoje).";
    if (devolucao.modo === null) return "Escolha quanto devolver à cliente.";
    if (devolucao.modo === "parte" && devolucao.valor <= 0) return "Informe quanto devolve.";
    if (devolucao.modo !== "nada" && (!devolucao.nome.trim() || !devolucao.pix.trim()))
      return "Informe quem recebe a devolução e o PIX.";
    if (corta) {
      if (devolucao.modo === "parte" && devolucao.valor > maxDevolucao)
        return `Acima do que dá para devolver (${brl(maxDevolucao)}).`;
      // A prévia recusou (a venda mudou, o dia foi cancelado no meio): a frase do servidor, nunca
      // "conferindo" para sempre.
      if (previa.isError) return previa.error?.message || "Não foi possível conferir a devolução mínima.";
      // A mínima é a da prévia dos valores de agora: a de antes (ou a que está chegando) não vale.
      if (!previa.emDia || previa.isFetching || previa.isPlaceholderData || efeito?.devolucao_minima === undefined)
        return "Conferindo a devolução mínima…";
      const minima = efeito.devolucao_minima;
      return (devolve ?? 0) < minima
        ? `Devolva pelo menos ${brl(minima)} ou aumente o novo valor da venda.`
        : null;
    }
    if (dados.com_nota && !impostoInformado) return "Informe o imposto retido (0 se não houve).";
    for (const bv of dados.bvs ?? []) {
      const conta = proporcional.get(bv.acrescimo_id);
      if (bv.pago || (conta !== undefined && conta <= 0)) continue;
      const entrada = bvs[bv.acrescimo_id];
      if ((bv.falta_recebedor && !entrada?.recebedor.trim()) || (bv.falta_pix && !entrada?.pix.trim()))
        return "Informe quem recebe o BV e o PIX.";
    }
    return null;
  }, [
    dados,
    cancelando,
    atualizando,
    motivo,
    outrosVivos,
    alcance,
    comDevolucao,
    corta,
    vendaNovaValida,
    devolucao,
    devolve,
    efeito,
    previa.emDia,
    previa.isFetching,
    previa.isPlaceholderData,
    previa.isError,
    previa.error,
    maxDevolucao,
    impostoInformado,
    bvs,
    proporcional,
  ]);

  function corpo(): CancelarEventoInput {
    const input: CancelarEventoInput = { motivo: motivo.trim() };
    if (outrosVivos && alcance) input.alcance = alcance;
    if (outrosVivos && alcance === "so_este_dia" && grupo?.proximo_principal) {
      input.novo_principal_id = grupo.proximo_principal.id;
    }
    if (corta) {
      input.venda_nova = vendaNova;
      input.venda_esperada = vendaDoGrupo;
    }
    if (!comDevolucao || devolucao.modo === null) return input;
    input.devolucao = { modo: devolucao.modo };
    if (devolucao.modo === "parte") input.devolucao.valor = devolucao.valor;
    if (devolucao.modo === "tudo") input.devolucao.valor = maxDevolucao;
    if (devolucao.modo !== "nada") {
      input.devolucao.nome = devolucao.nome.trim();
      input.devolucao.pix = devolucao.pix.trim();
      if (devolucao.observacao.trim()) input.devolucao.observacao = devolucao.observacao.trim();
    }
    if (corta) return input; // no corte, sem imposto e sem PIX de BV
    if (dados?.com_nota) input.imposto_retido = imposto;
    const completados = Object.entries(bvs)
      .filter(([, e]) => e.recebedor.trim() || e.pix.trim())
      .map(([id, e]) => ({ acrescimo_id: Number(id), recebedor: e.recebedor.trim(), pix: e.pix.trim() }));
    if (completados.length > 0) input.bvs = completados;
    return input;
  }

  function confirmar() {
    setErro("");
    setErros({});
    if (!dados) return;

    if (dados.acao === "excluir") {
      excluir.mutate(undefined, {
        onSuccess: (r) => {
          onOpenChange(false);
          navigate("/agenda", { state: { aviso: r.aviso ?? undefined } });
        },
        onError: (e) => setErro(e.message),
      });
      return;
    }
    if (pendencia) return;
    cancelar.mutate(corpo(), {
      onSuccess: () => onOpenChange(false),
      onError: (e) => {
        const codigo = codigoDaRecusa(e);
        if (codigo === "ja_cancelado") {
          queryClient.invalidateQueries({ queryKey: ["event", eventId] });
          onOpenChange(false);
          return;
        }
        if (codigo === "max_devolucao_mudou" || codigo === "grupo_mudou" || codigo === "sem_outro_dia_vivo") {
          setAlcance(null);
          setVendaEditada(false);
          void impacto.refetch();
        }
        if (e instanceof ApiRequestError && e.fields) setErros(e.fields);
        setErro(e.message);
      },
    });
  }

  const pendente = excluir.isPending || cancelar.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{dados?.acao === "excluir" ? "Excluir evento" : "Cancelar evento"}</DialogTitle>
        </DialogHeader>

        {impacto.isLoading && <Skeleton className="h-32 w-full" />}
        {impacto.isError && (
          <p className="text-sm text-red">Não foi possível carregar o impacto desta ação.</p>
        )}

        {dados && (
          <div className="max-h-[65vh] space-y-3 overflow-y-auto pr-1">
            <p className="text-sm text-ink">“{eventTitle}”</p>

            <ResumoImpacto impacto={dados} />

            {dados.acao === "excluir" && dados.is_group_leader && (
              <div className="rounded-md border border-red/40 bg-surface-2 p-3 text-sm" role="alert">
                <p className="font-semibold text-red">Este evento é o principal de um grupo comercial.</p>
                <p className="mt-1 text-ink">
                  Para excluí-lo, tire os satélites do grupo primeiro — na aba Comercial, no painel{" "}
                  <strong>Grupo comercial</strong>.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => {
                    onOpenChange(false);
                    navigate(`/events/${eventId}?aba=comercial`);
                  }}
                >
                  Ir para o painel do grupo
                </Button>
              </div>
            )}

            {dados.sumiu_do_google && (
              <p className="rounded-md border border-line bg-surface-2 p-3 text-sm text-ink" role="note">
                Este evento já não está no Google Agenda: nada será removido de lá.
              </p>
            )}

            {cancelando && (
              <>
                <div>
                  <label className={LABEL} htmlFor="motivo-cancelamento">
                    Motivo do cancelamento
                  </label>
                  <Input
                    id="motivo-cancelamento"
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                    placeholder="Ex.: cliente desistiu do evento"
                    aria-invalid={Boolean(erros.motivo)}
                  />
                  {erros.motivo && (
                    <p className="mt-1 text-xs text-red" role="alert">
                      {erros.motivo}
                    </p>
                  )}
                </div>

                {virtual && (
                  <p className="text-sm text-muted">
                    Venda da Loja Virtual: o dinheiro segue o pedido; aqui só o motivo.
                  </p>
                )}

                {grupo && (ehDia || outrosVivos) && (
                  <CancelamentoDiasBloco
                    eventId={eventId}
                    grupo={grupo}
                    ehDia={ehDia}
                    outrosVivos={outrosVivos}
                    alcance={alcance}
                    onAlcance={(a) => {
                      setAlcance(a);
                      // Trocar entre todos e só este muda o que cabe ("Tudo" não vale no corte).
                      if (a === "so_este_dia" && devolucao.modo === "tudo") setDevolucao((d) => ({ ...d, modo: null }));
                    }}
                    corta={corta}
                    vendaDoGrupo={vendaDoGrupo}
                    vendaNova={vendaNova}
                    onVendaNova={(v) => {
                      setVendaEditada(true);
                      setVendaNova(v);
                    }}
                    erros={erros}
                  />
                )}

                {comDevolucao && (!outrosVivos || alcance !== null) && (
                  <>
                    <CancelamentoDevolucaoBloco
                      state={devolucao}
                      onChange={(patch) => setDevolucao((d) => ({ ...d, ...patch }))}
                      pago={pago}
                      maxDevolucao={maxDevolucao}
                      comprovantesSemValor={dados.comprovantes_sem_valor ?? 0}
                      erros={erros}
                      semTudo={corta}
                      minima={corta ? (efeito?.devolucao_minima ?? 0) : 0}
                    />
                    {!corta && (
                    <CancelamentoBvBloco
                      bvs={dados.bvs ?? []}
                      proporcional={proporcional}
                      entradas={bvs}
                      onEntrada={(id, entrada) => setBvs((atual) => ({ ...atual, [id]: entrada }))}
                      erros={erros}
                    />
                    )}
                    {!corta && dados.com_nota && (
                      <fieldset className="rounded-md border border-line p-3">
                        <legend className="px-1 text-xs font-semibold uppercase text-muted">
                          Imposto sobre o retido
                        </legend>
                        <label className={LABEL} htmlFor="imposto-retido">
                          Imposto retido
                        </label>
                        <MoneyInput
                          id="imposto-retido"
                          className={FIELD}
                          value={imposto}
                          onValueChange={(v) => {
                            setImposto(v);
                            setImpostoInformado(true);
                          }}
                          aria-invalid={Boolean(erros.imposto_retido)}
                        />
                        <p className="mt-1 text-xs text-muted">
                          Referência: {formatBRL(dados.imposto_aliquota ?? 0)}% do retido
                          {efeito?.imposto_referencia != null && ` = ${brl(efeito.imposto_referencia)}`}. Vale o
                          que você informar.
                        </p>
                        {erros.imposto_retido && (
                          <p className="mt-1 text-xs text-red" role="alert">
                            {erros.imposto_retido}
                          </p>
                        )}
                      </fieldset>
                    )}
                    <EfeitoNaComissao efeito={efeito} carregando={previa.isFetching} />
                  </>
                )}
              </>
            )}

            {(erro || pendencia) && (
              <p className={`text-sm ${erro ? "text-red" : "text-muted"}`} role={erro ? "alert" : undefined}>
                {erro || pendencia}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Voltar
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-red"
            loading={pendente}
            disabled={
              !dados || (dados.acao === "excluir" && dados.is_group_leader) || (cancelando && pendencia !== null)
            }
            onClick={confirmar}
          >
            {dados?.acao === "excluir" ? "Excluir de vez" : "Cancelar evento"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
