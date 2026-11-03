import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Button, Skeleton } from "@manto/ui";
import { BlockCard, HELP } from "./shared";
import { dataBr, OrcamentoPicker } from "../OrcamentoPicker";
import type { OrcamentoHistoricoEntry } from "../../lib/orcamento";
import type { OrcamentoPrefill } from "../../lib/eventCreate";

export interface OrcamentoBlockProps {
  /** O `orcamento_id` do endereço — vinculado, mesmo que o pré-preenchimento ainda não tenha chegado. */
  orcamentoId: number | null;
  prefill: OrcamentoPrefill | undefined;
  carregando: boolean;
  erro: boolean;
  onTentarNovamente: () => void;
  onVincular: (entry: OrcamentoHistoricoEntry) => void;
  onDesvincular: () => void;
  /** A escolha da duração, que mexe no estado da página (preço da venda). */
  children?: ReactNode;
}

/**
 * Bloco "Orçamento" do Novo evento (feature 326): vincular o orçamento já feito sem sair da tela —
 * antes só se chegava com ele pelo "Criar evento" do histórico. Mesma busca e mesmos verbos da tela
 * do evento (feature 273: Trocar, Desvincular). Orçamento que já virou evento vivo é recusado aqui,
 * antes do Salvar: o `POST /api/events` responderia 409 (1:1 entre eventos vivos).
 */
export function OrcamentoBlock({
  orcamentoId,
  prefill,
  carregando,
  erro,
  onTentarNovamente,
  onVincular,
  onDesvincular,
  children,
}: OrcamentoBlockProps) {
  const [trocando, setTrocando] = useState(false);
  const [jaVirouEvento, setJaVirouEvento] = useState<OrcamentoHistoricoEntry | null>(null);

  const escolher = (entry: OrcamentoHistoricoEntry) => {
    if (entry.event_id != null) {
      setJaVirouEvento(entry);
      return;
    }
    setJaVirouEvento(null);
    setTrocando(false);
    onVincular(entry);
  };

  const busca = (
    <div className="space-y-2">
      <OrcamentoPicker onChange={escolher} />
      {jaVirouEvento && (
        <p role="alert" className="text-sm text-red">
          {`Este orçamento já virou o evento${jaVirouEvento.event_title ? ` “${jaVirouEvento.event_title}”` : ""}. `}
          Selecione outro orçamento ou{" "}
          <Link to={`/events/${jaVirouEvento.event_id}`} className="underline">
            abra o evento
          </Link>
          .
        </p>
      )}
    </div>
  );

  if (orcamentoId == null) {
    return (
      <BlockCard title="Orçamento" id="bloco-orcamento">
        <p className={HELP}>
          Vincule o orçamento já feito: os valores, o elenco e a nota vêm dele. O que já foi preenchido
          nesta tela continua.
        </p>
        {busca}
      </BlockCard>
    );
  }

  return (
    <BlockCard title="Orçamento" id="bloco-orcamento">
      {carregando && <Skeleton className="h-10 w-full" />}
      {erro && (
        <p role="alert" className="text-sm text-red">
          Não foi possível carregar o orçamento. Tente novamente.
        </p>
      )}
      {!carregando && !erro && !prefill?.orcamento_id && (
        <p role="alert" className="text-sm text-red">
          Orçamento não encontrado. Desvincule e selecione outro.
        </p>
      )}
      {prefill?.orcamento_id && (
        <>
          <p className="text-sm text-ink">
            Orçamento de <strong>{prefill.client_name || "cliente sem nome"}</strong>
            {[dataBr(prefill.date), prefill.location].filter(Boolean).map((parte) => (
              <span key={parte} className="text-muted">
                {" "}
                · {parte}
              </span>
            ))}
          </p>
          {children}
        </>
      )}
      {trocando ? (
        <>
          {busca}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setTrocando(false);
              setJaVirouEvento(null);
            }}
          >
            Cancelar
          </Button>
        </>
      ) : (
        <div className="flex flex-wrap gap-2">
          {erro && (
            <Button type="button" variant="outline" size="sm" onClick={onTentarNovamente}>
              Tentar novamente
            </Button>
          )}
          <Button type="button" variant="ghost" size="sm" onClick={() => setTrocando(true)}>
            Trocar
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={onDesvincular}>
            Desvincular
          </Button>
        </div>
      )}
    </BlockCard>
  );
}
