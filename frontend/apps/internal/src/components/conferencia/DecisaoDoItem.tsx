import { useEffect, useState } from "react";
import { cn } from "@manto/ui";
import { FigurinoPicker } from "../FigurinoPicker";
import {
  ROTULO_DO_TIPO,
  TIPOS_DO_ITEM,
  erroDoCampo,
  mensagemDoErro,
  useAlterarItem,
  type ConferenciaDoItem,
} from "../../lib/catalogoConferencia";

const EXPLICACAO: Record<string, string> = {
  tema: "Vários personagens com nome. Cada um ganha a própria ficha.",
  dupla: "Dois personagens com nome, vendidos juntos.",
  avulso: "Um personagem só. O item usa uma ficha direto, sem elenco.",
  generico: "Vários artistas com o mesmo figurino, sem nome próprio. Fica sem elenco.",
};

interface DecisaoDoItemProps {
  itemId: number;
  nomeDoItem: string;
  conferencia: ConferenciaDoItem;
  travado: boolean;
}

/**
 * O que se decide sobre o item em si: o tipo, a ficha (só em avulso) e a observação.
 *
 * Mudar o tipo não apaga nada: o elenco proposto e a ficha do item ficam guardados e voltam a valer
 * se o tipo voltar (FR-007). Por isso a troca é um toque, sem confirmação.
 */
export function DecisaoDoItem({ itemId, nomeDoItem, conferencia, travado }: DecisaoDoItemProps) {
  const alterar = useAlterarItem(itemId);
  const [observacao, setObservacao] = useState(conferencia.observacao ?? "");
  useEffect(() => setObservacao(conferencia.observacao ?? ""), [conferencia.observacao]);

  const bloqueado = travado || alterar.isPending;
  const erroDaObservacao = erroDoCampo(alterar.error, "observacao");
  const erroGeral = erroDaObservacao ? null : mensagemDoErro(alterar.error);
  const sugerida = conferencia.ficha_sugerida;

  function salvarObservacao() {
    if (!travado && observacao.trim() !== (conferencia.observacao ?? "")) alterar.mutate({ observacao });
  }

  return (
    <section className="space-y-3 rounded-lg border border-line bg-panel p-3" aria-label="Tipo do item">
      <div>
        <h2 className="text-sm font-semibold text-ink">Tipo do item</h2>
        {conferencia.tipo !== conferencia.tipo_lido && (
          <p className="text-xs text-muted">A leitura propôs: {ROTULO_DO_TIPO[conferencia.tipo_lido]}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="group" aria-label={`Tipo de ${nomeDoItem}`}>
        {TIPOS_DO_ITEM.map((tipo) => (
          <button
            key={tipo}
            type="button"
            disabled={bloqueado}
            aria-pressed={conferencia.tipo === tipo}
            onClick={() => conferencia.tipo !== tipo && alterar.mutate({ tipo })}
            className={cn(
              "h-11 rounded-md border text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              conferencia.tipo === tipo
                ? "border-accent bg-accent-soft text-accent"
                : "border-line bg-panel text-muted",
            )}
          >
            {ROTULO_DO_TIPO[tipo]}
          </button>
        ))}
      </div>
      <p className="text-xs text-muted">{EXPLICACAO[conferencia.tipo]}</p>

      {conferencia.tipo === "avulso" && (
        <div>
          <p className="mb-1 text-sm font-medium text-ink">Ficha de figurino do item</p>
          <FigurinoPicker
            value={conferencia.ficha?.id ?? null}
            onChange={(fichaId) => alterar.mutate({ ficha_id: fichaId })}
            characterName={nomeDoItem}
            disabled={bloqueado}
            ariaLabel={`Ficha de figurino de ${nomeDoItem}`}
            placeholder="Buscar ficha de figurino"
          />
          {sugerida && conferencia.ficha?.id !== sugerida.id && (
            <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted">
              <span>
                Ficha sugerida: {sugerida.id} {sugerida.nome}
              </span>
              <button
                type="button"
                className="min-h-11 font-medium text-accent underline disabled:opacity-60"
                disabled={bloqueado}
                onClick={() => alterar.mutate({ ficha_id: sugerida.id })}
              >
                Usar a sugerida
              </button>
            </div>
          )}
          {!conferencia.ficha && <p className="mt-1 text-xs text-muted">Sem ficha: o item fica pendente de ficha.</p>}
        </div>
      )}

      <div>
        <label className="mb-1 block text-sm font-medium text-ink" htmlFor={`observacao-item-${itemId}`}>
          Observação do item
        </label>
        <textarea
          id={`observacao-item-${itemId}`}
          className={cn(
            "h-20 w-full resize-y rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink disabled:opacity-60",
            erroDaObservacao && "border-red",
          )}
          value={observacao}
          disabled={travado}
          maxLength={1000}
          placeholder="Ex.: faltou um personagem, item parece duplicado"
          onChange={(e) => setObservacao(e.target.value)}
          onBlur={salvarObservacao}
        />
        {erroDaObservacao && <p className="mt-1 text-xs text-red">{erroDaObservacao}</p>}
      </div>

      <p className={cn("min-h-4 text-xs", erroGeral ? "text-red" : "text-muted")} aria-live="polite">
        {alterar.isPending ? "Salvando…" : (erroGeral ?? (alterar.isSuccess ? "Salvo." : ""))}
      </p>
    </section>
  );
}
