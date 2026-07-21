import { useEffect, useState } from "react";
import { API_BASE } from "@manto/api-client";
import { Button } from "@manto/ui";
import type { ClientLinkInput } from "../lib/eventCreate";

interface ClientResult {
  id: number;
  name: string;
  phone_display: string;
  company: string;
}

/** Busca clientes por nome/telefone (reusa `/clientes/search`, feature 114 — já JSON). */
function useClientSearch(query: string) {
  const [results, setResults] = useState<ClientResult[]>([]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${API_BASE}/clientes/search?q=${encodeURIComponent(q)}`, { credentials: "include" })
        .then((r) => (r.ok ? (r.json() as Promise<ClientResult[]>) : []))
        .then(setResults)
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  return results;
}

interface SelectedClient extends ClientLinkInput {
  name: string;
}

/**
 * Seleciona um ou mais clientes existentes com o tipo de relação (feature 114/152). Consome
 * `/clientes/search` diretamente (endpoint Jinja já-JSON) — sem endpoint `/api/*` novo.
 */
export function ClientPicker({
  value,
  onChange,
  relationOptions,
}: {
  value: SelectedClient[];
  onChange: (next: SelectedClient[]) => void;
  relationOptions: string[];
}) {
  const [query, setQuery] = useState("");
  const results = useClientSearch(query);
  const selectedIds = new Set(value.map((c) => c.client_id));

  const addClient = (c: ClientResult) => {
    if (selectedIds.has(c.id)) return;
    onChange([...value, { client_id: c.id, name: c.name, relation: "Contratante" }]);
    setQuery("");
  };

  const removeClient = (id: number) => onChange(value.filter((c) => c.client_id !== id));

  const setRelation = (id: number, relation: string) =>
    onChange(value.map((c) => (c.client_id === id ? { ...c, relation } : c)));

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <ul className="space-y-2">
          {value.map((c) => (
            <li key={c.client_id} className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-ink">{c.name}</span>
              <select
                className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                value={c.relation}
                onChange={(e) => setRelation(c.client_id, e.target.value)}
                aria-label={`Relação de ${c.name}`}
              >
                {relationOptions.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeClient(c.client_id)}
                aria-label={`Remover ${c.name}`}
              >
                ✕
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="relative">
        <input
          className="h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Buscar cliente por nome ou telefone…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Buscar cliente"
        />
        {results.length > 0 && (
          <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-line bg-panel shadow-md">
            {results.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left text-sm text-ink hover:bg-surface-2"
                  onClick={() => addClient(c)}
                >
                  {c.name}
                  {c.phone_display && (
                    <span className="ml-2 text-xs text-muted">{c.phone_display}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
