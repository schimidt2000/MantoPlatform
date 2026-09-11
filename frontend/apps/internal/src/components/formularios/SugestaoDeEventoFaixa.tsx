import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Button, ConfirmDialog, formatShortDate } from "@manto/ui";
import {
  mensagemDaApi,
  useConfirmarSugestao,
  useDescartarSugestao,
  type ResultadoVinculo,
} from "../../lib/formulariosAdmin";
import type { SugestaoDeEvento } from "../../lib/types";

/**
 * "Parece ser o evento de DD/MM — [Ligar] [Não é este]" (feature 298).
 *
 * A cliente já tem na agenda um evento a até 3 dias da data que ela informou, ainda sem
 * formulário. "Ligar" liga pelo núcleo (a cliente vem junto, o aviso some); "Não é este" pede
 * confirmação porque é definitivo — ligar à mão pela tela Formulários continua possível.
 *
 * A raiz é `motion.div` com `exit`: dentro de um `AnimatePresence` a faixa entra e sai animada
 * (e sem transição com movimento reduzido). `basis-full` a põe numa linha própria quando mora
 * dentro de uma linha flex que quebra.
 */
export function SugestaoDeEventoFaixa({
  formularioId,
  sugestao,
  onLigado,
}: {
  formularioId: number;
  sugestao: SugestaoDeEvento;
  /** Chamado com a resposta do "Ligar" — é por aqui que a divergência de cliente chega. */
  onLigado?: (resultado: ResultadoVinculo) => void;
}) {
  const reduceMotion = useReducedMotion();
  const confirmar = useConfirmarSugestao();
  const descartar = useDescartarSugestao();
  const [descartando, setDescartando] = useState(false);
  const alvo = { id: formularioId, eventId: sugestao.event_id };

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="basis-full overflow-hidden"
    >
      <div className="mt-2 flex flex-wrap items-center gap-2 rounded-md bg-accent-soft px-3 py-2 text-sm">
        <span className="min-w-0 flex-1 text-ink">
          Parece ser o evento de{" "}
          <strong className="tabular-nums">{formatShortDate(sugestao.data ?? null)}</strong>
          {sugestao.titulo && <span className="text-muted"> — {sugestao.titulo}</span>}
        </span>
        <div className="flex shrink-0 items-center gap-1.5">
          <Button
            type="button"
            size="sm"
            loading={confirmar.isPending}
            onClick={() => confirmar.mutate(alvo, { onSuccess: (resultado) => onLigado?.(resultado) })}
          >
            Ligar
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setDescartando(true)}>
            Não é este
          </Button>
        </div>
      </div>
      {confirmar.isError && (
        <p role="alert" className="mt-1 text-xs text-red">
          {mensagemDaApi(confirmar.error, "Não foi possível ligar. Tente novamente.")}
        </p>
      )}

      <ConfirmDialog
        open={descartando}
        title="Não é este evento?"
        description="A sugestão não voltará para este formulário. Ainda dá para ligar à mão pela tela Formulários."
        confirmLabel="Não é este"
        pending={descartar.isPending}
        error={descartar.isError ? mensagemDaApi(descartar.error, "Não foi possível descartar.") : null}
        onConfirm={() => descartar.mutate(alvo, { onSuccess: () => setDescartando(false) })}
        onOpenChange={(aberto) => {
          if (!aberto) {
            setDescartando(false);
            descartar.reset();
          }
        }}
      />
    </motion.div>
  );
}
