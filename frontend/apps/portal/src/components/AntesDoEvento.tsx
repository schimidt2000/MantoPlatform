import { useId, useState } from "react";
import { CalendarClock, ChevronDown } from "lucide-react";
import type { PortalBeforeEvent } from "../lib/portalAgenda";
import { formatDateTimeRange } from "../lib/format";

/**
 * O bloco "Antes do evento": ensaio, maquiagem e saída.
 *
 * **Recolhido por padrão, e ausente quando não há nada** — as duas coisas pelo mesmo motivo. O
 * card do artista já carrega título, data, função, cachê e os links de figurino e avaliação; o
 * pedido do dono foi explícito em não poluí-lo. Hoje a maioria dos eventos não tem ensaio nem
 * logística, e para esses o card continua do tamanho de antes, porque este componente devolve
 * `null`.
 *
 * A ordem dos itens é a **cronológica real** — ensaio (dias antes), maquiagem, saída —, que é a
 * sequência em que a pessoa vai vivê-los. Qualquer outra obriga quem lê a remontar a sequência de
 * cabeça, que é exatamente o trabalho que esta feature existe para poupar.
 *
 * O nome é um só, no bloco e no controle: "Antes do evento". Dois nomes para a mesma coisa é como
 * se descobre, tarde, que duas pessoas achavam que estavam falando de telas diferentes.
 */
export function AntesDoEvento({ bloco }: { bloco: PortalBeforeEvent | null | undefined }) {
  const [aberto, setAberto] = useState(false);
  const painelId = useId();

  if (!bloco) return null;
  const { makeup, departure, rehearsals } = bloco;
  if (!makeup && !departure && rehearsals.length === 0) return null;

  return (
    <div className="rounded-md border border-line bg-surface-2">
      {/* `min-h-[44px]` e a linha inteira clicável: o alvo de toque mínimo vale para o dedo de
          quem está na rua, não só para o cursor. `aria-expanded` + `aria-controls` são o que faz
          um leitor de tela anunciar o que o botão abre e se já está aberto. */}
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        aria-controls={painelId}
        className="flex min-h-[44px] w-full items-center gap-2 px-3 text-sm font-medium text-ink"
      >
        <CalendarClock className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
        Antes do evento
        <ChevronDown
          className={`ml-auto h-4 w-4 shrink-0 text-muted transition-transform ${
            aberto ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        />
      </button>

      {aberto && (
        <div id={painelId} className="space-y-2 border-t border-line px-3 py-2.5">
          {rehearsals.map((ensaio, i) => (
            <div key={`${ensaio.start_at}-${i}`}>
              <p className="text-sm text-ink">
                <span className="font-medium">Ensaio</span>{" "}
                {formatDateTimeRange(ensaio.start_at, ensaio.end_at)}
              </p>
              {ensaio.location && <p className="text-sm text-muted">{ensaio.location}</p>}
            </div>
          ))}

          {makeup?.time && (
            <p className="text-sm text-ink">
              <span className="font-medium">Maquiagem</span> {makeup.time}
              {makeup.location ? ` — ${makeup.location}` : ""}
            </p>
          )}

          {departure?.time && (
            <p className="text-sm text-ink">
              <span className="font-medium">Saída</span> {departure.time}
              {departure.location ? ` — ${departure.location}` : ""}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
