import { Link } from "react-router-dom";
import { Badge, Button, CopyButton, Skeleton, Table, TableCell, TableRow } from "@manto/ui";
import {
  useEmailBounces,
  useResolveBounce,
  type BounceKind,
  type EmailBounceItem,
} from "../lib/talents";

/** Vermelho para o que exige corrigir o cadastro; dourado para o que é só caixa cheia. */
const KIND_TONE: Record<BounceKind, "red" | "gold" | "neutral"> = {
  endereco_invalido: "red",
  dominio_invalido: "red",
  bloqueado: "neutral",
  caixa_cheia: "gold",
  outro: "neutral",
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** Link de conversa no WhatsApp a partir do telefone cadastrado (só dígitos). */
function whatsappHref(phone: string | null, message: string): string | null {
  const digits = (phone || "").replace(/\D/g, "");
  if (digits.length < 10) return null;
  const withCountry = digits.length <= 11 ? `55${digits}` : digits;
  return `https://wa.me/${withCountry}?text=${encodeURIComponent(message)}`;
}

function contactMessage(item: EmailBounceItem): string {
  const nome = (item.talent_name || "").split(" ")[0];
  const saudacao = nome ? `Oi, ${nome}! ` : "Oi! ";
  if (item.kind === "caixa_cheia") {
    return (
      `${saudacao}Aqui é da Manto Produções. Nossos emails estão voltando porque sua caixa de ` +
      `entrada (${item.email}) está cheia. Consegue liberar espaço para você receber os convites?`
    );
  }
  return (
    `${saudacao}Aqui é da Manto Produções. Nossos emails para ${item.email} estão voltando — ` +
    `parece que o endereço tem algum erro. Qual é o seu email correto?`
  );
}

function BounceRow({ item }: { item: EmailBounceItem }) {
  const resolve = useResolveBounce();
  const whatsapp = whatsappHref(item.talent_phone, contactMessage(item));

  return (
    <TableRow>
      <TableCell>
        {item.talent_id ? (
          <Link
            to={`/talents/${item.talent_id}`}
            className="font-medium text-ink hover:text-accent hover:underline"
          >
            {item.talent_name}
          </Link>
        ) : (
          <span className="font-medium text-ink">{item.user_name || "—"}</span>
        )}
        <div className="flex items-center gap-1 text-xs text-muted">
          <span className="truncate" title={item.email}>
            {item.email}
          </span>
          <CopyButton value={item.email} label="Copiar email" />
        </div>
      </TableCell>
      <TableCell>
        <Badge tone={KIND_TONE[item.kind]}>{item.kind_label}</Badge>
        {!item.is_permanent && (
          <div className="mt-0.5 text-[11px] text-muted">o servidor ainda está tentando</div>
        )}
      </TableCell>
      <TableCell className="hidden text-muted lg:table-cell">{item.action_hint}</TableCell>
      <TableCell align="right" className="whitespace-nowrap text-muted">
        {item.occurrences}×
      </TableCell>
      <TableCell className="hidden whitespace-nowrap text-muted md:table-cell">
        {formatDateTime(item.last_seen_at)}
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap justify-end gap-1.5">
          {whatsapp && (
            <Button asChild variant="outline" size="sm">
              <a href={whatsapp} target="_blank" rel="noopener noreferrer">
                WhatsApp
              </a>
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            loading={resolve.isPending}
            onClick={() => resolve.mutate({ email: item.email })}
          >
            Resolver
          </Button>
        </div>
        {resolve.isError && <p className="text-right text-xs text-red">Não foi possível.</p>}
      </TableCell>
    </TableRow>
  );
}

/**
 * Fila de emails devolvidos (feature 219).
 *
 * Existe porque a falha de entrega só aparecia como um aviso do Mail Delivery Subsystem na caixa
 * de quem envia — invisível para o sistema. Aqui ela vira lista de contato, separando "caixa
 * cheia" (avisar para liberar espaço) de "endereço errado" (pegar o email certo e corrigir).
 */
export function BounceQueue() {
  const query = useEmailBounces(true);

  if (query.isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
        Não foi possível carregar a fila de emails devolvidos.
      </div>
    );
  }

  const items = query.data?.items ?? [];
  if (items.length === 0) {
    return (
      <p className="rounded-md border border-line bg-panel px-4 py-6 text-center text-sm text-muted">
        Nenhum email devolvido pendente. 🎉
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        {items.length} pessoa(s) não estão recebendo nossos emails. A varredura roda sozinha a cada
        30 minutos; "Resolver" tira da fila depois do contato — e corrigir o email na ficha também.
      </p>
      <div className="rounded-md border border-line bg-panel">
        <Table>
          <thead>
            <TableRow head>
              <TableCell as="th">Pessoa</TableCell>
              <TableCell as="th">Motivo</TableCell>
              <TableCell as="th" className="hidden lg:table-cell">
                O que fazer
              </TableCell>
              <TableCell as="th" align="right">
                Falhas
              </TableCell>
              <TableCell as="th" className="hidden md:table-cell">
                Última
              </TableCell>
              <TableCell as="th" className="text-right">
                Ações
              </TableCell>
            </TableRow>
          </thead>
          <tbody>
            {items.map((item) => (
              <BounceRow key={item.email} item={item} />
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  );
}
