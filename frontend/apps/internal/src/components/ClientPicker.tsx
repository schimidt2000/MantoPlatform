import { useState } from "react";
import { Button } from "@manto/ui";
import { useClientSearch, useQuickCreateClient, type ClientSummary } from "../lib/clientes";
import type { ClientLinkInput } from "../lib/eventCreate";

interface SelectedClient extends ClientLinkInput {
  name: string;
}

const FIELD = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Cadastro rápido de cliente inline (feature 184) — nome/telefone/empresa, sem sair do
 * formulário de evento. Reaproveita `useQuickCreateClient()` (feature 165): cria ou aproveita um
 * cliente já existente pelo telefone informado. */
function QuickCreateClientForm({
  onCreated,
  onCancel,
}: {
  onCreated: (client: ClientSummary) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ name?: string; phone?: string }>({});
  const create = useQuickCreateClient();

  const submit = () => {
    const errors: { name?: string; phone?: string } = {};
    if (!name.trim()) errors.name = "Nome completo é obrigatório.";
    if (!phone.trim()) errors.phone = "Telefone é obrigatório.";
    setFieldErrors(errors);
    if (errors.name || errors.phone) return;

    create.mutate(
      { name: name.trim(), phone: phone.trim(), company: company.trim() || undefined },
      { onSuccess: (result) => onCreated(result) },
    );
  };

  return (
    <div className="space-y-2 rounded-md border border-line bg-surface-2 p-3">
      <div className="grid gap-2 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs text-muted">Nome completo *</label>
          <input
            className={FIELD}
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Nome completo"
          />
          {fieldErrors.name && <p className="mt-1 text-xs text-red">{fieldErrors.name}</p>}
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Telefone com DDD *</label>
          <input
            className={FIELD}
            placeholder="(11) 98765-4321"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            aria-label="Telefone com DDD"
          />
          {fieldErrors.phone && <p className="mt-1 text-xs text-red">{fieldErrors.phone}</p>}
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Empresa (opcional)</label>
          <input
            className={FIELD}
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            aria-label="Empresa"
          />
        </div>
      </div>
      {create.isError && <p className="text-xs text-red">Não foi possível cadastrar o cliente.</p>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="button" size="sm" loading={create.isPending} onClick={submit}>
          Salvar e adicionar
        </Button>
      </div>
    </div>
  );
}

/**
 * Seleciona um ou mais clientes existentes com o tipo de relação (feature 114/152). Consome
 * `/api/clientes/search` (feature 165) via `useClientSearch` — fonte única de busca de cliente,
 * reusada por qualquer tela que precise selecionar cliente existente.
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
  const [creating, setCreating] = useState(false);
  const search = useClientSearch(query);
  const results = search.data ?? [];
  const selectedIds = new Set(value.map((c) => c.client_id));

  const addClient = (c: ClientSummary) => {
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
      {!creating && (
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
      )}

      {creating ? (
        <QuickCreateClientForm
          onCreated={(client) => {
            addClient(client);
            setCreating(false);
          }}
          onCancel={() => setCreating(false)}
        />
      ) : (
        <Button type="button" variant="outline" size="sm" onClick={() => setCreating(true)}>
          + Cadastrar novo cliente
        </Button>
      )}
    </div>
  );
}
