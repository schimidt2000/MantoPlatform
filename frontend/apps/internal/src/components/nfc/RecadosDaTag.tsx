import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import { MessageSquareHeart } from "lucide-react";
import {
  Badge,
  Button,
  cn,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  formatShortDate,
  Skeleton,
} from "@manto/ui";
import {
  useMarcarRecadosLidos,
  useNfcTags,
  useRecadosDaTag,
  type NfcRecado,
} from "../../lib/nfc";

export interface RecadosDaTagProps {
  tagId: number;
  onFechar: () => void;
}

/**
 * `12/09/2026 às 14:32` — a data sai de `formatShortDate` (fonte única do design system) e a
 * hora vem colada porque um recado é um momento: "hoje de manhã" e "de madrugada" contam
 * história diferente, e a listagem perde isso se mostrar só o dia.
 */
function formatarDataHora(iso: string): string {
  const data = formatShortDate(iso);
  const quando = new Date(iso);
  if (Number.isNaN(quando.getTime())) return data;
  const hora = quando.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${data} às ${hora}`;
}

const LISTA: Variants = {
  oculta: {},
  visivel: {},
};

const ITEM: Variants = {
  oculta: { opacity: 0, y: 10 },
  // O atraso é por índice em vez de `staggerChildren` para poder ter TETO: numa tag muito
  // querida o escalonamento puro deixaria o último recado entrando quase um segundo depois.
  // O carinho está no conteúdo, não na espera — a lista assenta em 0,3 s no pior caso.
  visivel: (indice: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.22, delay: Math.min(indice * 0.04, 0.3), ease: "easeOut" },
  }),
};

/** Um recado na tela: o texto grande, a assinatura pequena embaixo. */
interface RecadoItemProps {
  recado: NfcRecado;
  indice: number;
  naoLido: boolean;
}

function RecadoItem({ recado, indice, naoLido }: RecadoItemProps) {
  return (
    <motion.li
      custom={indice}
      variants={ITEM}
      className={cn(
        "rounded-md border border-line bg-surface p-4",
        // Marca do não lido: um fio de acento na lateral. Discreto de propósito — o recado é
        // da cliente, não um alerta do sistema; nada de fundo colorido gritando na leitura.
        naoLido && "border-l-2 border-l-accent",
      )}
    >
      {/* `whitespace-pre-wrap` guarda as quebras de linha que a pessoa digitou; `break-words`
          impede que uma palavra colada sem espaço estoure a largura do diálogo. */}
      <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-ink">
        {recado.message}
      </p>
      <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
        {recado.author_name && (
          <>
            <span className="font-medium text-ink">{recado.author_name}</span>
            <span aria-hidden="true">·</span>
          </>
        )}
        <span>{formatarDataHora(recado.created_at)}</span>
        {naoLido && <Badge tone="accent">novo</Badge>}
      </p>
    </motion.li>
  );
}

/**
 * Recados que a cliente escreveu na página da tag (feature 297) — a primeira via de volta que
 * a luminária tem.
 *
 * O diálogo fica aberto enquanto estiver montado (`open` fixo): quem decide fechar é o pai,
 * pelo `onFechar`. O nº humano da tag sai da lista de gestão já em cache (`useNfcTags`) — a
 * resposta de `/recados` só traz os recados, e mostrar o id do banco no título seria um número
 * que ninguém da equipe reconhece (o que se anota na tagzinha é o `sequence`).
 *
 * A leitura é marcada assim que os recados chegam, mas as marcas de "novo" continuam na tela
 * até o diálogo fechar: elas vêm de um retrato tirado na abertura, não da resposta viva. Sem
 * esse retrato o `invalidate` da mutation devolveria tudo já lido e os selos sumiriam debaixo
 * dos olhos de quem abriu justamente para ver o que era novo.
 */
export function RecadosDaTag({ tagId, onFechar }: RecadosDaTagProps) {
  const reduceMotion = useReducedMotion();
  const { data: listaTags } = useNfcTags();
  const query = useRecadosDaTag(tagId);
  const marcar = useMarcarRecadosLidos();
  const { mutate: marcarComoLidos } = marcar;

  const [abertura, setAbertura] = useState<{ tagId: number; naoLidos: ReadonlySet<number> } | null>(
    null,
  );

  const dados = query.data;

  useEffect(() => {
    // Espera os recados chegarem: disparar a marcação junto com a busca é corrida — a resposta
    // podia voltar já lida e a tela abriria sem nenhuma marca de novo.
    if (!dados || abertura?.tagId === tagId) return;
    const naoLidos = new Set(dados.items.filter((r) => r.read_at === null).map((r) => r.id));
    setAbertura({ tagId, naoLidos });
    if (naoLidos.size > 0) marcarComoLidos(tagId);
  }, [dados, tagId, abertura, marcarComoLidos]);

  const recados = useMemo(() => {
    // Mais novo primeiro. O servidor não promete ordem, e o desempate por id mantém estável a
    // lista quando dois recados caem no mesmo segundo.
    return [...(dados?.items ?? [])].sort((a, b) => {
      if (a.created_at === b.created_at) return b.id - a.id;
      return a.created_at < b.created_at ? 1 : -1;
    });
  }, [dados]);

  const tag = listaTags?.tags.find((t) => t.id === tagId) ?? null;
  const titulo = tag ? `Recados — tag nº ${tag.sequence}` : "Recados da tag";
  const naoLidosNaAbertura = abertura?.tagId === tagId ? abertura.naoLidos : null;

  function estaNaoLido(recado: NfcRecado): boolean {
    return naoLidosNaAbertura ? naoLidosNaAbertura.has(recado.id) : recado.read_at === null;
  }

  return (
    <Dialog open onOpenChange={(aberto) => !aberto && onFechar()}>
      <DialogContent open className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>
            O que quem recebeu a luminária escreveu ao encostar o celular na peça
            {tag && ` — ${tag.item.name}`}.
          </DialogDescription>
        </DialogHeader>

        {query.isLoading && (
          <div className="space-y-3" aria-label="Carregando os recados">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}

        {query.isError && (
          <div className="space-y-3" role="alert">
            <p className="text-sm text-red">
              Não foi possível carregar os recados agora. Nada se perdeu — eles continuam
              guardados.
            </p>
            <Button
              variant="outline"
              size="sm"
              loading={query.isFetching}
              onClick={() => void query.refetch()}
            >
              Tentar de novo
            </Button>
          </div>
        )}

        {!query.isLoading && !query.isError && recados.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <MessageSquareHeart className="h-7 w-7 text-muted" aria-hidden="true" />
            <p className="text-sm text-muted">
              Nenhum recado ainda — quem recebeu a luminária ainda não escreveu.
            </p>
          </div>
        )}

        {recados.length > 0 && (
          <motion.ul
            // `initial={false}` com movimento reduzido: os itens nascem já no lugar, sem
            // deslocamento nem fade (Princípio XI).
            initial={reduceMotion ? false : "oculta"}
            animate="visivel"
            variants={LISTA}
            className="max-h-[60vh] space-y-3 overflow-y-auto pr-1"
          >
            {recados.map((recado, indice) => (
              <RecadoItem
                key={recado.id}
                recado={recado}
                indice={indice}
                naoLido={estaNaoLido(recado)}
              />
            ))}
          </motion.ul>
        )}

        {marcar.isError && (
          <p className="mt-3 text-xs text-muted" role="status">
            Os recados continuam marcados como não lidos — o servidor não confirmou a leitura.
          </p>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={onFechar}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
