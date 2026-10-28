import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { copyToClipboard } from "../../lib/clipboard";
import { useUpdateNotaFiscal } from "../../lib/eventOps";
import { mensagemDaApi } from "../../lib/formulariosAdmin";
import { diaMes } from "../../lib/homeListas";
import { hojeYmd } from "../../lib/horaLocal";
import { formatarDoc, type NotaAEmitir } from "../../lib/notaFiscal";

/** "2026-10-28T14:02:11" (horário de SP) → "28/10 às 14:02" — recorte de string, sem `Date`. */
function quandoPediu(iso: string | null): string | null {
  const dia = diaMes(iso);
  return dia && iso ? `${dia} às ${iso.slice(11, 16)}` : dia;
}

/**
 * Uma nota pedida (feature 323): o que o site da prefeitura pede, a discriminação para copiar e o
 * PDF inserido ali mesmo — inserir emite a nota e a tira da lista.
 */
function LinhaNotaAEmitir({ nota }: { nota: NotaAEmitir }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [copiou, setCopiou] = useState<boolean | null>(null);
  const inserir = useUpdateNotaFiscal(nota.event_id);
  const pedida = quandoPediu(nota.pedida_em);
  const doc = formatarDoc(nota.tomador.doc);

  const copiar = async () => {
    setCopiou(await copyToClipboard(nota.discriminacao));
    setTimeout(() => setCopiou(null), 2000);
  };

  return (
    <li className="space-y-2 py-3 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="font-semibold tabular-nums text-ink">
          {nota.amount != null ? `R$ ${formatBRL(nota.amount)}` : "Valor a definir"}
        </span>
        <span className="flex flex-wrap items-center gap-1.5">
          <Badge tone="red">Urgente</Badge>
          {nota.iss_retido && <Badge tone="gold">ISS retido · {nota.municipio}</Badge>}
          {nota.cancelado && <Badge tone="neutral">Evento cancelado</Badge>}
        </span>
      </div>

      <div className="text-ink">
        {nota.tomador.nome ?? "Cliente não informado"}
        <span className={doc ? "text-muted" : "font-medium text-red"}>
          {" · "}
          {doc || "CNPJ não informado"}
        </span>
        {(nota.tomador.email || nota.tomador.endereco) && (
          <span className="block break-words text-muted">
            {[nota.tomador.email, nota.tomador.endereco].filter(Boolean).join(" · ")}
          </span>
        )}
      </div>
      <div className="text-muted">
        <Link to={`/events/${nota.event_id}?aba=comercial`} className="text-blue underline">
          {nota.event_title}
        </Link>
        {diaMes(nota.event_start_at) && ` · ${diaMes(nota.event_start_at)}`}
        {nota.pedida_por && ` · pedida por ${nota.pedida_por}`}
        {pedida && ` em ${pedida}`}
      </div>

      <pre className="whitespace-pre-wrap rounded-md bg-surface-2/60 p-3 font-sans text-sm text-ink">
        {nota.discriminacao}
      </pre>

      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="outline" onClick={copiar}>
          {copiou ? "Discriminação copiada" : "Copiar discriminação"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,image/*"
          className="hidden"
          aria-label={`PDF da nota de ${nota.tomador.nome ?? nota.event_title}`}
          onChange={(e) => {
            const file = e.target.files?.[0];
            // O PATCH grava valor e data do corpo: sem eles o valor da nota seria apagado.
            if (file) {
              inserir.mutate({
                id: nota.id,
                amount: nota.amount != null ? String(nota.amount) : "",
                issue_date: nota.issue_date ?? hojeYmd(),
                file,
              });
            }
            e.target.value = "";
          }}
        />
        <Button size="sm" loading={inserir.isPending} onClick={() => inputRef.current?.click()}>
          Inserir nota
        </Button>
      </div>
      {copiou === false && (
        <p role="alert" className="text-xs text-red">
          Não foi possível copiar. Selecione o texto acima e copie manualmente.
        </p>
      )}
      {inserir.isError && (
        <p role="alert" className="text-xs text-red">
          {mensagemDaApi(inserir.error, "Não foi possível inserir a nota. Tente novamente.")}
        </p>
      )}
    </li>
  );
}

/** O painel da tela inicial do Superadmin: toda nota pedida e ainda não emitida. */
export function PainelNotasAEmitir({ itens }: { itens: NotaAEmitir[] }) {
  if (itens.length === 0) {
    return <p className="py-2 text-sm text-muted">Nenhuma nota a emitir.</p>;
  }
  return (
    <ul className="divide-y divide-line">
      {itens.map((nota) => (
        <LinhaNotaAEmitir key={nota.id} nota={nota} />
      ))}
    </ul>
  );
}
