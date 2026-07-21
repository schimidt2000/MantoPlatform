import { useEffect, useState } from "react";
import { API_BASE } from "@manto/api-client";
import { Button } from "@manto/ui";

interface FormResponseResult {
  id: number;
  name: string;
  phone_display: string;
  form_type: string;
  event_date: string;
  created_at: string;
}

/** Busca respostas de pré-contrato (reusa `/formularios/respostas/search`, já JSON). */
function useFormResponseSearch(query: string) {
  const [results, setResults] = useState<FormResponseResult[]>([]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${API_BASE}/formularios/respostas/search?q=${encodeURIComponent(q)}`, {
        credentials: "include",
      })
        .then((r) => (r.ok ? (r.json() as Promise<FormResponseResult[]>) : []))
        .then(setResults)
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  return results;
}

export interface SelectedFormResponse {
  id: number;
  name: string;
  form_type: string;
}

/**
 * Vincula uma resposta de pré-contrato já recebida ao evento (feature 118/152). Seleção única —
 * consome `/formularios/respostas/search` direto (endpoint Jinja já-JSON).
 */
export function FormResponsePicker({
  value,
  onChange,
}: {
  value: SelectedFormResponse | null;
  onChange: (next: SelectedFormResponse | null) => void;
}) {
  const [query, setQuery] = useState("");
  const results = useFormResponseSearch(query);

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
        placeholder="Buscar resposta por nome, telefone ou data…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Buscar pré-contrato"
      />
      {results.length > 0 && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-line bg-panel shadow-md">
          {results.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                className="block w-full px-3 py-2 text-left text-sm text-ink hover:bg-surface-2"
                onClick={() => {
                  onChange({ id: r.id, name: r.name, form_type: r.form_type });
                  setQuery("");
                }}
              >
                {r.name}
                <span className="ml-2 text-xs text-muted">
                  {r.form_type} · {r.created_at}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
