import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { PosEventoDialog } from "../components/EventDetail/PosEventoDialog";
import {
  dataCurta,
  usePosEventoLista,
  type ItemDoPosEvento,
  type SituacaoDoPosEvento,
} from "../lib/baseAutorizada";

const SITUACAO: Record<SituacaoDoPosEvento, { rotulo: string; tom: "neutral" | "green" | "blue" }> = {
  pendente: { rotulo: "Pendente", tom: "neutral" },
  copiado: { rotulo: "Copiado", tom: "blue" },
  conversa: { rotulo: "Enviado", tom: "green" },
};

function Linha({ item, onAbrir }: { item: ItemDoPosEvento; onAbrir: () => void }) {
  const situacao = SITUACAO[item.situacao];
  return (
    <li className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <Link to={`/events/${item.event_id}`} className="block truncate font-medium text-ink hover:underline">
          {item.titulo}
        </Link>
        <p className="truncate text-sm text-muted">
          {[dataCurta(item.start_at), item.cliente?.name ?? "Sem contratante"].join(" · ")}
        </p>
        <div className="mt-1 flex flex-wrap gap-1.5">
          <Badge tone={situacao.tom}>
            {situacao.rotulo}
            {item.registrado_em ? ` em ${dataCurta(item.registrado_em)}` : ""}
          </Badge>
          {item.avaliacao_recebida && <Badge tone="gold">Avaliação recebida</Badge>}
        </div>
      </div>
      <Button
        variant={item.situacao === "pendente" ? "default" : "outline"}
        size="sm"
        className="min-h-11 shrink-0"
        onClick={onAbrir}
      >
        {item.situacao === "pendente" ? "Preparar mensagem" : "Ver mensagem"}
      </Button>
    </li>
  );
}

/**
 * Pós-evento (feature 350): os eventos dos últimos 7 dias, do mais recente. A equipe prepara uma
 * mensagem só — fotos, avaliação, indicação e o convite para receber novidades — no dia seguinte.
 * Nada sai sozinho: copiar ou enviar pela conversa é decisão de quem atende.
 */
export function PosEventoPage() {
  const lista = usePosEventoLista();
  const [aberto, setAberto] = useState<number | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const reduzir = useReducedMotion();
  const itens = lista.data?.items ?? [];
  const pendentes = itens.filter((i) => i.situacao === "pendente").length;

  return (
    <div className="mx-auto max-w-[900px] space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/clientes">‹ Clientes</Link>
      </Button>
      <PageHeader
        title="Pós-evento"
        subtitle={
          lista.data
            ? pendentes === 1
              ? "1 evento esperando a mensagem do dia seguinte"
              : `${pendentes} eventos esperando a mensagem do dia seguinte`
            : undefined
        }
      />
      {aviso && (
        <p className="rounded-md bg-green-soft px-3 py-2 text-sm text-green" role="status">
          {aviso}
        </p>
      )}
      <Card>
        <CardContent className="pt-4">
          {lista.isLoading && <Skeleton className="h-40 w-full" />}
          {lista.isError && (
            <p className="text-sm text-red" role="alert">
              Não foi possível carregar a lista. Tente novamente.
            </p>
          )}
          {lista.data && itens.length === 0 && (
            <p className="text-sm text-muted">Nenhum evento nos últimos 7 dias.</p>
          )}
          {itens.length > 0 && (
            <motion.ul
              initial={reduzir ? false : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: reduzir ? 0 : 0.2 }}
              className="divide-y divide-line"
            >
              {itens.map((item) => (
                <Linha key={item.event_id} item={item} onAbrir={() => setAberto(item.event_id)} />
              ))}
            </motion.ul>
          )}
        </CardContent>
      </Card>
      <PosEventoDialog eventId={aberto} onClose={() => setAberto(null)} onAviso={setAviso} />
    </div>
  );
}
