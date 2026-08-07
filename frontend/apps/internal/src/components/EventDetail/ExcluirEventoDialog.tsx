import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
import { formatBRL, MoneyInput } from "@manto/money";
import {
  useCancelarEvento,
  useDeleteEvent,
  useImpactoExclusao,
  type ImpactoExclusao,
} from "../../lib/eventOps";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

/** Painel que explica o que está preso no evento — é o que decide entre excluir e cancelar. */
function ResumoImpacto({ impacto }: { impacto: ImpactoExclusao }) {
  const comissoesPagas = impacto.comissoes.filter((c) => c.status === "pago");
  const linhas: string[] = [];
  if (impacto.sale_value > 0) linhas.push(`Venda de ${brl(impacto.sale_value)}`);
  if (impacto.total_recebido > 0)
    linhas.push(`${brl(impacto.total_recebido)} já recebidos da cliente`);
  if (impacto.tem_contrato) linhas.push("Contrato anexado");
  if (impacto.elenco.length > 0) linhas.push(`${impacto.elenco.length} pessoa(s) escalada(s)`);
  if (comissoesPagas.length > 0)
    linhas.push(
      `Comissão já paga a ${comissoesPagas.map((c) => c.seller_name ?? "—").join(", ")}`,
    );
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
    <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="alert">
      <p className="font-semibold text-gold-ink">
        Este evento tem coisa presa — será cancelado, não excluído.
      </p>
      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink">
        {linhas.map((linha) => (
          <li key={linha}>{linha}</li>
        ))}
      </ul>
      <p className="mt-2 text-ink">
        O registro continua existindo (é a ele que a devolução se refere), mas o evento sai da
        agenda, das vendas, da DRE e da planilha de pagamentos. A comissão já paga vira estorno
        no próximo repasse do vendedor.
      </p>
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
 * Diálogo único de excluir/cancelar (feature 224). O servidor decide qual das duas ações vale
 * (`impacto.acao`) e a tela explica o porquê antes de qualquer confirmação — o diálogo antigo
 * só perguntava "tem certeza?", e foi assim que um evento com pagamento recebido foi apagado.
 */
export function ExcluirEventoDialog({
  eventId,
  eventTitle,
  open,
  onOpenChange,
}: ExcluirEventoDialogProps) {
  const navigate = useNavigate();
  const impacto = useImpactoExclusao(eventId, open);
  const excluir = useDeleteEvent(eventId);
  const cancelar = useCancelarEvento(eventId);

  const [motivo, setMotivo] = useState("");
  const [valor, setValor] = useState(0);
  const [nome, setNome] = useState("");
  const [pix, setPix] = useState("");
  const [erro, setErro] = useState("");

  // Pré-preenche a devolução com o que a cliente pagou — é o valor que se devolve por padrão.
  useEffect(() => {
    if (!impacto.data) return;
    setValor(impacto.data.devolucao_sugerida);
    setNome(impacto.data.cliente_nome ?? "");
  }, [impacto.data]);

  useEffect(() => {
    if (!open) {
      setMotivo("");
      setPix("");
      setErro("");
    }
  }, [open]);

  const dados = impacto.data;
  const pendente = excluir.isPending || cancelar.isPending;

  function confirmar() {
    setErro("");
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

    if (!motivo.trim()) {
      setErro("Explique o motivo do cancelamento.");
      return;
    }
    cancelar.mutate(
      {
        motivo,
        devolucao: valor > 0 ? { valor, nome, pix } : undefined,
      },
      {
        onSuccess: () => onOpenChange(false),
        onError: (e) => setErro(e.message),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {dados?.acao === "excluir" ? "Excluir evento" : "Cancelar evento"}
          </DialogTitle>
        </DialogHeader>

        {impacto.isLoading && <Skeleton className="h-32 w-full" />}
        {impacto.isError && (
          <p className="text-sm text-red">Não foi possível carregar o impacto desta ação.</p>
        )}

        {dados && (
          <div className="space-y-3">
            <p className="text-sm text-ink">“{eventTitle}”</p>

            <ResumoImpacto impacto={dados} />

            {dados.is_group_leader && (
              <p className="text-sm text-red" role="alert">
                Este evento é o principal de um grupo comercial. Desagrupe os satélites antes.
              </p>
            )}

            {dados.acao === "cancelar" && (
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
                  />
                </div>

                <div className="rounded-md border border-line p-3">
                  <p className="mb-2 text-xs font-semibold uppercase text-muted">
                    Devolução à cliente
                  </p>
                  <p className="mb-2 text-xs text-muted">
                    Entra como saída aprovada em Gastos Extras e aparece na Planilha de
                    Pagamentos. Deixe zerado se não há nada a devolver.
                  </p>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div>
                      <label className={LABEL} htmlFor="devolucao-valor">
                        Valor
                      </label>
                      <MoneyInput
                        id="devolucao-valor"
                        className={FIELD}
                        value={valor}
                        onValueChange={setValor}
                        aria-label="Valor a devolver"
                      />
                    </div>
                    <div>
                      <label className={LABEL} htmlFor="devolucao-nome">
                        Quem recebe
                      </label>
                      <Input
                        id="devolucao-nome"
                        value={nome}
                        onChange={(e) => setNome(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className={LABEL} htmlFor="devolucao-pix">
                        PIX
                      </label>
                      <Input
                        id="devolucao-pix"
                        value={pix}
                        onChange={(e) => setPix(e.target.value)}
                      />
                    </div>
                  </div>
                  {valor > 0 && dados.total_recebido > 0 && valor !== dados.total_recebido && (
                    <p className="mt-2 text-xs text-gold-ink">
                      A cliente pagou {brl(dados.total_recebido)} — você está devolvendo{" "}
                      {brl(valor)}.
                    </p>
                  )}
                </div>
              </>
            )}

            {erro && (
              <p className="text-sm text-red" role="alert">
                {erro}
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
            disabled={!dados || dados.is_group_leader}
            onClick={confirmar}
          >
            {dados?.acao === "excluir" ? "Excluir de vez" : "Cancelar evento"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
