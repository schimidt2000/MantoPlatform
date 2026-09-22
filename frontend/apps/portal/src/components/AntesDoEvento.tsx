import { CalendarClock } from "lucide-react";
import { AccordionRow } from "@manto/ui";
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
 *
 * A expansão é o `AccordionRow` de `@manto/ui` (feature 187), não um `useState` próprio: ele já
 * traz altura animada com Framer Motion respeitando `useReducedMotion`, mais `aria-expanded` e
 * `aria-controls` — foi escrito para a "Resumo por Vendedor" do financeiro, mas é genérico. A
 * primeira versão desta tela reimplementou tudo isso à mão e ficou sem animação nenhuma. O alvo
 * de toque de 44px vem pelo `summary`, que é quem dá altura ao botão.
 */
export function AntesDoEvento({ bloco }: { bloco: PortalBeforeEvent | null | undefined }) {
  if (!bloco) return null;
  // `?? []` pelo mesmo motivo que os campos novos nascem opcionais (FR-013b): o site e a API
  // sobem como serviços separados, e um bloco vindo de uma versão diferente do servidor pode não
  // trazer a lista. `undefined.length` aqui derrubaria a árvore inteira e o card viraria tela
  // branca no celular — que é exatamente o acidente que esta feature se deu ao trabalho de evitar
  // do outro lado, mantendo `history` no payload.
  const { makeup, departure } = bloco;
  const rehearsals = bloco.rehearsals ?? [];
  if (!makeup && !departure && rehearsals.length === 0) return null;

  return (
    <div className="rounded-md border border-line bg-surface-2 px-3">
      <AccordionRow
        summary={
          <span className="flex min-h-[44px] items-center gap-2 text-sm font-medium text-ink">
            <CalendarClock className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
            Antes do evento
          </span>
        }
        contentClassName="space-y-2"
      >
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
      </AccordionRow>
    </div>
  );
}
