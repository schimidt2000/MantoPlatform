import type { ReactNode } from "react";
import { SEVERIDADE_FUNDO, type Severidade } from "../../lib/homeListas";

/**
 * A casca de uma linha comercial da Home (298, 299): quem e quando no cabeçalho, o detalhe embaixo
 * e a ação à direita.
 *
 * Em tela estreita o conteúdo quebra em várias linhas e o botão desce, sem rolagem horizontal — a
 * ação principal fica sempre à mostra e nada do que aparece no computador é escondido (FR-030).
 * `children` é o que se abre por baixo da linha (a sugestão de evento, os repetidos).
 */
export function LinhaDaHome({
  severidade,
  cabecalho,
  detalhe,
  acoes,
  children,
}: {
  severidade: Severidade;
  cabecalho: ReactNode;
  detalhe?: ReactNode;
  acoes: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-2.5 text-sm ${SEVERIDADE_FUNDO[severidade]}`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-medium text-ink">{cabecalho}</div>
        {detalhe && <div className="text-muted">{detalhe}</div>}
      </div>
      <div className="flex shrink-0 items-center gap-1.5">{acoes}</div>
      {children}
    </div>
  );
}
