import { useState } from "react";
import { Button, ConfirmDialog } from "@manto/ui";
import {
  mensagemDoErro,
  useGravarNoCatalogo,
  useResumoDaGravacao,
  type LoteGravado,
} from "../../lib/catalogoConferencia";

function plural(quantidade: number, um: string, varios: string): string {
  return `${quantidade} ${quantidade === 1 ? um : varios}`;
}

/**
 * Grava no catálogo o que a conferência aprovou (feature 364).
 *
 * É o único ponto da conferência que muda a vitrine: cria os personagens dos temas e duplas
 * conferidos e liga a ficha dos avulsos. Por isso pede confirmação. O servidor grava em lotes;
 * o andamento aparece aqui até acabar, e repetir não cria nada em dobro.
 */
export function GravarNoCatalogo() {
  const resumo = useResumoDaGravacao();
  const [andamento, setAndamento] = useState<LoteGravado | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const gravar = useGravarNoCatalogo(setAndamento);
  const falta = resumo.data?.itens_a_gravar ?? 0;
  const total = andamento ? andamento.itens_gravados + andamento.restantes : falta;

  if (!resumo.data || (falta === 0 && !andamento && !gravar.error)) return null;

  return (
    <section className="space-y-2 rounded-lg border border-line bg-panel p-4" aria-label="Gravar no catálogo">
      <h2 className="text-sm font-semibold text-ink">Gravar no catálogo</h2>
      {gravar.isPending ? (
        <p className="text-sm text-ink" aria-live="polite">
          Gravando… {andamento?.itens_gravados ?? 0} de {total} itens
        </p>
      ) : andamento ? (
        <p className="text-sm text-ink" aria-live="polite">
          Gravação concluída: {plural(andamento.itens_gravados, "item", "itens")},{" "}
          {plural(andamento.personagens_criados, "personagem criado", "personagens criados")} e{" "}
          {plural(andamento.fichas_ligadas, "ficha ligada", "fichas ligadas")}.
        </p>
      ) : (
        <p className="text-sm text-ink">
          {plural(falta, "item conferido pronto", "itens conferidos prontos")} para gravar:{" "}
          {plural(resumo.data.personagens_a_criar, "personagem", "personagens")} e{" "}
          {plural(resumo.data.fichas_a_ligar, "ficha", "fichas")}.
        </p>
      )}
      {andamento && andamento.falhas.length > 0 && (
        <ul className="space-y-1 text-sm text-red">
          {andamento.falhas.map((falha) => (
            <li key={falha.id}>
              {falha.nome}: {falha.motivo}
            </li>
          ))}
        </ul>
      )}
      {gravar.error && <p className="text-sm text-red">{mensagemDoErro(gravar.error)}</p>}
      {(falta > 0 || gravar.isPending) && (
        <Button loading={gravar.isPending} onClick={() => setConfirmando(true)}>
          Gravar no catálogo
        </Button>
      )}
      <ConfirmDialog
        open={confirmando}
        title="Gravar no catálogo?"
        description="Os personagens conferidos passam a aparecer no catálogo e na vitrine. Itens já gravados não são repetidos."
        confirmLabel="Gravar"
        pending={false}
        onConfirm={() => {
          setConfirmando(false);
          gravar.mutate();
        }}
        onOpenChange={setConfirmando}
      />
    </section>
  );
}
