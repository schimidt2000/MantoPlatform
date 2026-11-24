import { Link } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { Button } from "@manto/ui";
import {
  mensagemDoErro,
  quandoConferiu,
  useConferirItem,
  useReabrirItem,
  type ConferenciaDoItem,
  type SituacaoDoItem,
} from "../../lib/catalogoConferencia";

interface RodapeDaConferenciaProps {
  itemId: number;
  situacao: SituacaoDoItem;
  /** Fora da fila (já tem elenco ou ficha no catálogo) não se confere nem se reabre. */
  naFila: boolean;
  conferencia: ConferenciaDoItem | null;
  anteriorId: number | null;
  proximoId: number | null;
  /** Endereço da fila, com o filtro em uso. */
  fila: string;
  onIrPara: (itemId: number) => void;
}

/**
 * A ação principal do item, presa ao pé da tela para ficar ao alcance do polegar (FR-018).
 *
 * "Conferir e ir para o próximo" só troca de item depois que o servidor confirma: se a conferência
 * for recusada (tema sem personagem a criar), a pessoa continua no item, com o motivo na frente.
 */
export function RodapeDaConferencia({
  itemId,
  situacao,
  naFila,
  conferencia,
  anteriorId,
  proximoId,
  fila,
  onIrPara,
}: RodapeDaConferenciaProps) {
  const conferir = useConferirItem(itemId);
  const reabrir = useReabrirItem(itemId);
  const erro = mensagemDoErro(conferir.error) ?? mensagemDoErro(reabrir.error);
  const conferido = situacao === "conferido";
  const podeConferir = situacao === "a_conferir" && naFila;

  function conferirEAvancar() {
    conferir.mutate(undefined, {
      onSuccess: () => {
        if (proximoId) onIrPara(proximoId);
      },
    });
  }

  return (
    <footer className="sticky bottom-0 z-20 -mx-4 space-y-2 border-t border-line bg-panel px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3 sm:-mx-6 sm:px-6">
      {erro && (
        <p className="text-sm text-red" role="alert">
          {erro}
        </p>
      )}
      {conferido && conferencia && (
        <p className="text-sm text-muted">
          {conferencia.conferido_por ? `Conferido por ${conferencia.conferido_por}` : "Conferido"}
          {conferencia.conferido_em ? ` em ${quandoConferiu(conferencia.conferido_em)}` : ""}.
          {!proximoId && (
            <>
              {" "}
              Nenhum outro item a conferir neste filtro.{" "}
              <Link to={fila} className="font-medium text-accent underline">
                Ver a fila
              </Link>
            </>
          )}
        </p>
      )}
      {/* "Anterior" é só o ícone: com o rótulo, os três botões do item conferido passam de 390 px. */}
      <div className="flex flex-wrap items-center gap-2">
        {anteriorId !== null && (
          <Button
            variant="outline"
            size="lg"
            className="w-12 px-0"
            aria-label="Item anterior a conferir"
            onClick={() => onIrPara(anteriorId)}
          >
            <ChevronLeft className="h-5 w-5" aria-hidden />
          </Button>
        )}
        {podeConferir && (
          <Button size="lg" className="min-w-0 flex-1 px-4" loading={conferir.isPending} onClick={conferirEAvancar}>
            {proximoId ? "Conferir e ir para o próximo" : "Conferir"}
          </Button>
        )}
        {conferido && naFila && (
          <Button variant="outline" size="lg" className="px-4" loading={reabrir.isPending} onClick={() => reabrir.mutate()}>
            Reabrir
          </Button>
        )}
        {!podeConferir && proximoId !== null && (
          <Button size="lg" className="min-w-0 flex-1 px-4" onClick={() => onIrPara(proximoId)}>
            Próximo a conferir
          </Button>
        )}
      </div>
    </footer>
  );
}
