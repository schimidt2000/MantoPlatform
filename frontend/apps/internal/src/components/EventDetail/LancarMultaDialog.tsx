import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import type { ResumoCancelado } from "../../lib/agenda";
import { useLancarMultas } from "../../lib/eventOps";
import { MultaAoElencoBloco, type LinhaDeMulta } from "./MultaAoElencoBloco";

/** Dias entre duas datas `AAAA-MM-DD` (pela string, em UTC: sem fuso nem horário de parede). */
function diasEntre(de: string | null | undefined, ate: string | null | undefined): number | null {
  if (!de || !ate) return null;
  const [a1, m1, d1] = de.slice(0, 10).split("-").map(Number);
  const [a2, m2, d2] = ate.slice(0, 10).split("-").map(Number);
  if (!a1 || !a2) return null;
  return Math.round((Date.UTC(a2, m2 - 1, d2) - Date.UTC(a1, m1 - 1, d1)) / 86_400_000);
}

interface LancarMultaDialogProps {
  eventId: number;
  resumo: ResumoCancelado;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * "Lançar multa ao elenco" depois do cancelamento (feature 306, FR-072): pelas linhas congeladas no
 * ato (quem estava escalado), inclusive quem o Casting já tirou da vaga. A multa já lançada fica só
 * leitura — corrige-se em Gastos Extras. Só aparece pela flag `can_edit_venda_cancelado`.
 */
export function LancarMultaDialog({ eventId, resumo, open, onOpenChange }: LancarMultaDialogProps) {
  const lancar = useLancarMultas(eventId);
  const [valores, setValores] = useState<Record<number, number>>({});
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!open) {
      setValores({});
      setErros({});
      setErro("");
    }
  }, [open]);

  const linhas: LinhaDeMulta[] = (resumo.elenco ?? []).map((e) => ({
    chave: e.elenco_id,
    artista: e.artista,
    vaga: e.vaga,
    dia: e.dia.data,
    cacheReferencia: e.cache_referencia,
    // Quantos dias faltavam do cancelamento ao dia da vaga (a referência da multa).
    faltamDias: diasEntre(resumo.cancelado_em, e.dia.data),
    semPix: !e.talent_pix_informado,
    jaLancada: e.multa ? e.multa.valor : null,
    foraDaVaga: !e.na_vaga,
  }));
  const algum = Object.values(valores).some((v) => v > 0);

  function salvar() {
    setErros({});
    setErro("");
    const multas = Object.entries(valores)
      .filter(([, v]) => v > 0)
      .map(([id, valor]) => ({ elenco_id: Number(id), valor }));
    lancar.mutate(
      { multas },
      {
        onSuccess: () => onOpenChange(false),
        onError: (e) => {
          if (e instanceof ApiRequestError && (e.status === 404 || e.status === 405)) {
            setErro("O sistema está atualizando — tente em um minuto.");
            return;
          }
          if (e instanceof ApiRequestError && e.fields) setErros(e.fields);
          setErro(e.message);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Lançar multa ao elenco</DialogTitle>
          <DialogDescription>
            Quem estava escalado no cancelamento. Cada multa vira um Gasto Extra aprovado, com a data de hoje.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          <MultaAoElencoBloco
            linhas={linhas}
            valores={valores}
            onValor={(chave, valor) => setValores((atual) => ({ ...atual, [chave]: valor }))}
            erros={erros}
            titulo="Escalações do cancelamento"
          />
          {(erro || erros.multas) && (
            <p className="text-sm text-red" role="alert">
              {erros.multas ?? erro}
            </p>
          )}
          {!algum && !erro && !erros.multas && (
            <p className="text-sm text-muted">Informe a multa de ao menos um artista.</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Voltar
          </Button>
          <Button size="sm" loading={lancar.isPending} disabled={!algum} onClick={salvar}>
            Lançar multa
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
