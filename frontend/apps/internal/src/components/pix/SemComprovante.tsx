import { useRef } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button } from "@manto/ui";
import { apiFetch } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import { enviarComprovante } from "../../lib/eventAttachments";
import { mensagemDaApi } from "../../lib/formulariosAdmin";

/**
 * A tarefa "incluir o comprovante do PIX" (decisão do dono, 23/10): o PIX lido do aviso do banco já
 * entrou na venda como recebido, mas o comprovante oficial (PDF do app do banco) é de gente —
 * Comercial, Financeiro ou Superadmin anexam aqui; o Financeiro é avisado no sino.
 */
export interface PagamentoSemComprovante {
  pagamento_id: number;
  event_id: number;
  titulo: string | null;
  data: string | null;
  valor: string | null;
  conta: string | null;
  pagador: string | null;
  recebido_em: string | null;
  automatico: boolean;
}

export function usePixSemComprovante() {
  return useQuery({
    queryKey: ["pix", "sem-comprovante"],
    queryFn: () => apiFetch<{ itens: PagamentoSemComprovante[] }>("/api/pix/sem-comprovante"),
  });
}

function quando(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function LinhaSemComprovante({ item }: { item: PagamentoSemComprovante }) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const incluir = useMutation({
    mutationFn: (file: File) =>
      enviarComprovante(item.event_id, {
        amount: Number(item.valor ?? 0),
        file,
        anexarA: item.pagamento_id,
      }),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["pix"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
      queryClient.invalidateQueries({ queryKey: ["event", item.event_id] });
    },
  });
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3 text-sm">
      <span className="w-28 shrink-0 font-medium tabular-nums text-ink">
        {item.valor ? `R$ ${formatBRL(Number(item.valor))}` : "—"}
      </span>
      <span className="min-w-0 flex-1">
        <Link to={`/events/${item.event_id}?aba=comercial`} className="text-blue underline">
          {item.titulo ?? "venda"}
        </Link>
        <span className="block text-muted">
          PIX · {item.conta ?? "conta não cadastrada"} · {quando(item.recebido_em)}
          {item.pagador && ` · de ${item.pagador}`}
        </span>
      </span>
      <Badge tone={item.automatico ? "green" : "blue"}>{item.automatico ? "automático" : "confirmado"}</Badge>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,image/*"
        className="hidden"
        aria-label={`Comprovante do PIX de ${item.titulo ?? "venda"}`}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) incluir.mutate(file);
          e.target.value = "";
        }}
      />
      <Button size="sm" loading={incluir.isPending} onClick={() => inputRef.current?.click()}>
        Incluir comprovante
      </Button>
      {incluir.isError && (
        <p role="alert" className="w-full text-xs text-red">
          {mensagemDaApi(incluir.error, "Não foi possível incluir o comprovante.")}
        </p>
      )}
    </li>
  );
}

export function ListaSemComprovante() {
  const lista = usePixSemComprovante();
  if (lista.isLoading) return <p className="text-sm text-muted">Carregando…</p>;
  if (lista.isError) {
    return (
      <p role="alert" className="text-sm text-red">
        Não foi possível carregar a lista.
      </p>
    );
  }
  const itens = lista.data?.itens ?? [];
  if (itens.length === 0) {
    return (
      <p className="rounded-md border border-line bg-panel px-4 py-6 text-center text-sm text-muted">
        Todo PIX ligado a uma venda já tem comprovante.
      </p>
    );
  }
  return (
    <div className="rounded-md border border-line bg-panel px-4">
      <p className="pt-3 text-xs text-muted">
        O valor já conta como recebido na venda. Falta o comprovante do banco (PDF do app do Inter).
      </p>
      <ul className="divide-y divide-line">
        {itens.map((item) => (
          <LinhaSemComprovante key={item.pagamento_id} item={item} />
        ))}
      </ul>
    </div>
  );
}
