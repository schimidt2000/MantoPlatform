import { useEffect, useState } from "react";
import { apiFetch } from "@manto/api-client";
import { Button } from "@manto/ui";

/** Item de `GET /api/formularios/respostas/search` (`_response_summary`). */
interface FormResponseResult {
  id: number;
  form_type: string;
  form_type_label: string;
  contact_name: string;
  contact_phone_display: string;
  event_date: string | null;
  created_at: string;
}

type EstadoBusca =
  | { status: "vazio" }
  | { status: "buscando" }
  | { status: "ok"; itens: FormResponseResult[] }
  | { status: "erro" };

/**
 * Busca respostas de pré-contrato.
 *
 * Usa `/api/formularios/respostas/search`, **não** a rota Jinja `/formularios/respostas/search`:
 * o servidor do frontend só repassa ao Flask os prefixos listados em `frontend/server.js`, e
 * `/formularios` não está lá (não pode estar — `/formularios` é rota do React Router). Apontada
 * para fora de `/api`, a chamada caía no fallback da SPA, recebia o `index.html` com status 200 e
 * morria no `JSON.parse` — o buscador ficava mudo, sem erro nenhum na tela.
 */
function useFormResponseSearch(query: string): EstadoBusca {
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
      apiFetch<{ responses: FormResponseResult[] }>(
        `/api/formularios/respostas/search?q=${encodeURIComponent(q)}`,
      )
        .then((data) => {
          if (!cancelado) setEstado({ status: "ok", itens: data.responses ?? [] });
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

/** "2026-08-15" / ISO com hora → "15/08/2026". Recorte de string, sem `Date` (ver horaLocal.ts). */
function dataBr(iso: string | null): string {
  if (!iso) return "";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes && ano ? `${dia}/${mes}/${ano}` : "";
}

export interface SelectedFormResponse {
  id: number;
  name: string;
  form_type: string;
}

const CAIXA =
  "absolute z-10 mt-1 w-full rounded-md border border-line bg-panel px-3 py-2 text-sm shadow-md";

/**
 * Vincula uma resposta de pré-contrato já recebida ao evento (feature 118/152). Seleção única.
 */
export function FormResponsePicker({
  value,
  onChange,
}: {
  value: SelectedFormResponse | null;
  onChange: (next: SelectedFormResponse | null) => void;
}) {
  const [query, setQuery] = useState("");
  const estado = useFormResponseSearch(query);

  if (value) {
    return (
      <div className="flex items-center gap-2">
        <div>
          <div className="text-sm font-medium text-ink">{value.name}</div>
          <div className="text-xs text-muted">{value.form_type}</div>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={() => onChange(null)}>
          Trocar
        </Button>
      </div>
    );
  }

  return (
    <div className="relative">
      <input
        className="h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder="Buscar resposta por nome, telefone ou data do evento…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Buscar pré-contrato"
      />

      {estado.status === "buscando" && <div className={`${CAIXA} text-muted`}>Buscando…</div>}

      {estado.status === "erro" && (
        <div className={`${CAIXA} text-red`} role="alert">
          Não foi possível buscar as respostas agora. Tente de novo em instantes.
        </div>
      )}

      {estado.status === "ok" && estado.itens.length === 0 && (
        <div className={`${CAIXA} text-muted`}>
          Nenhuma resposta encontrada para “{query.trim()}”.
        </div>
      )}

      {estado.status === "ok" && estado.itens.length > 0 && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-line bg-panel shadow-md">
          {estado.itens.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                className="block w-full px-3 py-2 text-left text-sm text-ink hover:bg-surface-2"
                onClick={() => {
                  onChange({ id: r.id, name: r.contact_name, form_type: r.form_type_label });
                  setQuery("");
                }}
              >
                {r.contact_name}
                <span className="ml-2 text-xs text-muted">
                  {[r.form_type_label, r.contact_phone_display, dataBr(r.event_date)]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
