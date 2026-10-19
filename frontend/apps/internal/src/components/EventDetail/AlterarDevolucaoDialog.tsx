import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
} from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { formatBRL, MoneyInput } from "@manto/money";
import type { ResumoCancelado } from "../../lib/agenda";
import { codigoDaRecusa, useAlterarDevolucao } from "../../lib/eventOps";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";
const FIELD =
  "h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-blue";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

interface AlterarDevolucaoDialogProps {
  eventId: number;
  resumo: ResumoCancelado;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * "Alterar devolução" do cancelado (feature 306, FR-017): o novo total devolvido, nome, PIX,
 * observação e imposto. Piso e teto vêm do servidor (`limites_devolucao`); o BV não tem campo,
 * porque acompanha o retido. Só aparece pela flag `can_edit_venda_cancelado`.
 */
export function AlterarDevolucaoDialog({ eventId, resumo, open, onOpenChange }: AlterarDevolucaoDialogProps) {
  const alterar = useAlterarDevolucao(eventId);
  // Feature 306, H5: no `dia`, o total é o daquele dia (o servidor manda em `limites.atual`); o
  // `devolvido` do resumo é o do grupo inteiro e duplicaria a devolução ao salvar.
  const doDia = resumo.regime === "dia";
  const inicial = resumo.limites_devolucao?.atual ?? resumo.devolvido;
  const [total, setTotal] = useState(inicial);
  const [nome, setNome] = useState("");
  const [pix, setPix] = useState("");
  const [observacao, setObservacao] = useState("");
  const [imposto, setImposto] = useState(resumo.imposto ?? 0);
  const [mexeuImposto, setMexeuImposto] = useState(false);
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (open) {
      setTotal(inicial);
      setImposto(resumo.imposto ?? 0);
      setMexeuImposto(false);
    } else {
      setNome("");
      setPix("");
      setObservacao("");
      setErros({});
      setErro("");
    }
  }, [open, inicial, resumo.imposto]);

  const limites = resumo.limites_devolucao;
  const comImposto = resumo.regime === "venda" && resumo.com_nota;

  function salvar() {
    setErros({});
    setErro("");
    alterar.mutate(
      {
        devolucao_total: total,
        ...(nome.trim() ? { nome: nome.trim() } : {}),
        ...(pix.trim() ? { pix: pix.trim() } : {}),
        ...(observacao.trim() ? { observacao: observacao.trim() } : {}),
        ...(comImposto && mexeuImposto ? { imposto_retido: imposto } : {}),
      },
      {
        onSuccess: () => onOpenChange(false),
        onError: (e) => {
          if (e instanceof ApiRequestError && (e.status === 404 || e.status === 405)) {
            setErro("O sistema está atualizando — tente em um minuto.");
            return;
          }
          if (e instanceof ApiRequestError && e.fields) setErros(e.fields);
          // O 409 do piso e do teto é sobre o novo total: a frase vai ao campo, não ao rodapé.
          const codigo = codigoDaRecusa(e);
          if (codigo === "abaixo_do_piso" || codigo === "acima_do_teto") {
            setErros({ devolucao_total: e.message });
            return;
          }
          setErro(e.message);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Alterar devolução</DialogTitle>
          <DialogDescription>
            {doDia ? (
              <>
                O total devolvido por este dia. Hoje: {brl(inicial)} neste dia; o grupo devolveu{" "}
                {brl(resumo.devolvido)} de {brl(resumo.pago)} pagos.{" "}
                {resumo.limites_devolucao?.refaz_retido
                  ? "O retido e a comissão do retido do 1º dia, já cancelado, acompanham o novo total."
                  : "A venda do grupo não muda."}
              </>
            ) : (
              <>
                O retido, a comissão e o BV acompanham o novo total. Hoje: devolvidos {brl(resumo.devolvido)} de{" "}
                {brl(resumo.pago)} pagos.
              </>
            )}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className={LABEL} htmlFor="novo-total-devolvido">
              {doDia ? "Novo total devolvido neste dia" : "Novo total devolvido"}
            </label>
            <MoneyInput
              id="novo-total-devolvido"
              className={FIELD}
              value={total}
              onValueChange={setTotal}
              aria-invalid={Boolean(erros.devolucao_total)}
            />
            {limites && (
              <p className="mt-1 text-xs text-muted">
                {doDia
                  ? `Entre ${brl(limites.piso)} (o mínimo do corte, ou o já pago ou no banco) e ${brl(limites.teto)} (o pago do grupo menos as devoluções dos outros dias).`
                  : `Entre ${brl(limites.piso)} (já pago ou no banco) e ${brl(limites.teto)}.`}
              </p>
            )}
            {erros.devolucao_total && (
              <p className="mt-1 text-xs text-red" role="alert">
                {erros.devolucao_total}
              </p>
            )}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className={LABEL} htmlFor="alterar-devolucao-nome">
                Quem recebe (se mudar)
              </label>
              <Input
                id="alterar-devolucao-nome"
                value={nome}
                maxLength={200}
                onChange={(e) => setNome(e.target.value)}
                aria-invalid={Boolean(erros.devolucao_nome)}
              />
              {erros.devolucao_nome && (
                <p className="mt-1 text-xs text-red" role="alert">
                  {erros.devolucao_nome}
                </p>
              )}
            </div>
            <div>
              <label className={LABEL} htmlFor="alterar-devolucao-pix">
                PIX (se mudar)
              </label>
              <Input
                id="alterar-devolucao-pix"
                value={pix}
                maxLength={120}
                onChange={(e) => setPix(e.target.value)}
                aria-invalid={Boolean(erros.devolucao_pix)}
              />
              {erros.devolucao_pix && (
                <p className="mt-1 text-xs text-red" role="alert">
                  {erros.devolucao_pix}
                </p>
              )}
            </div>
          </div>
          <div>
            <label className={LABEL} htmlFor="alterar-devolucao-obs">
              Observação (opcional)
            </label>
            <Input id="alterar-devolucao-obs" value={observacao} onChange={(e) => setObservacao(e.target.value)} />
          </div>
          {comImposto && (
            <div>
              <label className={LABEL} htmlFor="alterar-imposto">
                Imposto retido
              </label>
              <MoneyInput
                id="alterar-imposto"
                className={FIELD}
                value={imposto}
                onValueChange={(v) => {
                  setImposto(v);
                  setMexeuImposto(true);
                }}
                aria-invalid={Boolean(erros.imposto_retido)}
              />
              {erros.imposto_retido && (
                <p className="mt-1 text-xs text-red" role="alert">
                  {erros.imposto_retido}
                </p>
              )}
            </div>
          )}
          {erro && (
            <p className="text-sm text-red" role="alert">
              {erro}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={alterar.isPending}>
            Voltar
          </Button>
          <Button size="sm" onClick={salvar} loading={alterar.isPending}>
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
