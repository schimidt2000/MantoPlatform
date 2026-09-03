import { useEffect, useState } from "react";
import { apiFetch } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import type { OrcamentoHistoricoEntry, OrcamentoHistoricoResponse } from "../lib/orcamento";

type EstadoBusca =
  | { status: "vazio" }
  | { status: "buscando" }
  | { status: "ok"; itens: OrcamentoHistoricoEntry[] }
  | { status: "erro" };

/**
 * Busca no histórico de orçamentos (`GET /api/orcamento/historico?q=`, que filtra por cliente e
 * local e já respeita o dono: comercial só vê os próprios, superadmin vê todos). Mesmo desenho do
 * `FormResponsePicker`: debounce de 250 ms, cancelamento da resposta atrasada, estados explícitos.
 */
function useOrcamentoSearch(query: string): EstadoBusca {
  const [estado, setEstado] = useState<EstadoBusca>({ status: "vazio" });

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setEstado({ status: "vazio" });
      return;
    }
    setEstado({ status: "buscando" });
    let cancelado = false;
    const timer = setTimeout(() => {
      apiFetch<OrcamentoHistoricoResponse>(`/api/orcamento/historico?q=${encodeURIComponent(q)}`)
        .then((data) => {
          if (!cancelado) setEstado({ status: "ok", itens: (data.entries ?? []).slice(0, 20) });
        })
        .catch(() => {
          if (!cancelado) setEstado({ status: "erro" });
        });
    }, 250);
    return () => {
      cancelado = true;
      clearTimeout(timer);
    };
  }, [query]);

  return estado;
}

/** "2026-08-15" → "15/08/2026" por recorte de string (ver `lib/horaLocal.ts`) — `new Date("2026-08-15")`
 * é meia-noite UTC e mostraria o dia anterior em São Paulo. */
export function dataBr(iso: string | null | undefined): string {
  if (!iso) return "";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes && ano ? `${dia}/${mes}/${ano}` : "";
}

const CAIXA =
  "absolute z-10 mt-1 w-full rounded-md border border-line bg-panel px-3 py-2 text-sm shadow-md";

/**
 * Escolhe um orçamento salvo para vincular ao evento (feature 273). Seleção única; quem decide o
 * que fazer com a escolha (vincular, aplicar valores) é o painel que o usa.
 */
export function OrcamentoPicker({
  onChange,
  placeholder = "Buscar orçamento por cliente ou local…",
}: {
  onChange: (entry: OrcamentoHistoricoEntry) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const estado = useOrcamentoSearch(query);

  return (
    <div className="relative">
      <input
        className="h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Buscar orçamento"
      />

      {estado.status === "buscando" && <div className={`${CAIXA} text-muted`}>Buscando…</div>}

      {estado.status === "erro" && (
        <div className={`${CAIXA} text-red`} role="alert">
          Não foi possível buscar os orçamentos agora. Tente de novo em instantes.
        </div>
      )}

      {estado.status === "ok" && estado.itens.length === 0 && (
        <div className={`${CAIXA} text-muted`}>Nenhum orçamento encontrado para “{query.trim()}”.</div>
      )}

      {estado.status === "ok" && estado.itens.length > 0 && (
        <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-line bg-panel shadow-md">
          {estado.itens.map((entry) => (
            <li key={entry.id}>
              <button
                type="button"
                className="block w-full px-3 py-2 text-left text-sm text-ink hover:bg-surface-2"
                onClick={() => {
                  onChange(entry);
                  setQuery("");
                }}
              >
                <span className="font-medium">{entry.client_name || "Sem cliente"}</span>
                <span className="ml-2 text-xs text-muted">
                  {[dataBr(entry.event_date), entry.event_location, `2h ${formatBRL(entry.total_2h)}`]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
                {entry.event_id != null && (
                  <span className="ml-2 text-xs text-gold-ink">
                    já vinculado{entry.event_title ? `: ${entry.event_title}` : " a um evento"}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
