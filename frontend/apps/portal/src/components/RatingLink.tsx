import { Link } from "react-router-dom";
import { Star } from "lucide-react";
import { usePendingRatings } from "../lib/portalRatings";

/**
 * Rótulo e destino do link de avaliação de uma apresentação.
 *
 * O terceiro caso — já avaliado, fora da janela de edição — não existia: o link simplesmente
 * sumia, e com ele qualquer caminho até o que o artista escreveu. A tela de avaliação já sabe se
 * apresentar em modo leitura (o backend serve a avaliação sem limite de prazo), então só faltava
 * alguém apontar para ela.
 */
function rotuloAvaliacao(avaliado: boolean, podeAvaliar: boolean, podeEditar: boolean): string | null {
  if (podeEditar) return "Editar minha avaliação";
  if (avaliado) return "Ver minha avaliação";
  if (podeAvaliar) return "Avaliar este evento";
  return null;
}

export interface RatingLinkProps {
  eventId: number;
  className?: string;
}

/**
 * Link "Avaliar este evento" de uma apresentação passada (feature 229).
 *
 * Saiu de dentro de `PortalHistoricoPage` para virar fonte única quando a **seção Histórico da
 * Agenda** passou a precisar do mesmo botão. Motivo do relato que originou isso: a artista via as
 * apresentações dela na Agenda, com o crachá de pendência aceso na aba Histórico, e nenhum caminho
 * para avaliar no lugar onde estava olhando — as duas listas se chamam "Histórico", então ela não
 * tinha por que procurar a segunda.
 *
 * Ele mesmo consulta `usePendingRatings()` em vez de receber os conjuntos por prop: é a **mesma**
 * query key do shell (o crachá da aba lê dela), então o TanStack devolve do cache e o botão nunca
 * discorda do número em cima do ícone.
 */
export function RatingLink({ eventId, className }: RatingLinkProps) {
  const { data } = usePendingRatings();

  const avaliado = data?.rated_event_ids.includes(eventId) ?? false;
  const podeAvaliar = data?.rateable_event_ids.includes(eventId) ?? false;
  const podeEditar = data?.editable_event_ids.includes(eventId) ?? false;

  const rotulo = rotuloAvaliacao(avaliado, podeAvaliar, podeEditar);
  if (!rotulo) return null;

  return (
    <Link
      to={`/eventos/${eventId}/avaliar`}
      className={
        className ??
        "inline-flex min-h-[44px] items-center gap-2 text-sm font-medium text-accent hover:underline"
      }
    >
      <Star
        className="h-4 w-4"
        aria-hidden="true"
        // Estrela preenchida sinaliza, já na lista, que esta apresentação tem avaliação.
        fill={avaliado ? "currentColor" : "none"}
      />
      {rotulo}
    </Link>
  );
}
