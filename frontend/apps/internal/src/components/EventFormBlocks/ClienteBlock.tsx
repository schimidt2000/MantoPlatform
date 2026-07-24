import { LABEL, BlockCard } from "./shared";
import { ClientPicker } from "../ClientPicker";
import { FormResponsePicker, type SelectedFormResponse } from "../FormResponsePicker";
import type { ClientLinkInput } from "../../lib/eventCreate";

export interface ClienteBlockProps {
  clients: (ClientLinkInput & { name: string })[];
  onClientsChange: (next: (ClientLinkInput & { name: string })[]) => void;
  relationOptions: string[];
  formResponse: SelectedFormResponse | null;
  onFormResponseChange: (next: SelectedFormResponse | null) => void;
}

/** Bloco 1 — Cliente e pré-contrato (feature 184). */
export function ClienteBlock({
  clients,
  onClientsChange,
  relationOptions,
  formResponse,
  onFormResponseChange,
}: ClienteBlockProps) {
  return (
    <BlockCard title="Cliente e pré-contrato" id="bloco-cliente">
      <div>
        <label className={LABEL}>Clientes associados</label>
        <ClientPicker value={clients} onChange={onClientsChange} relationOptions={relationOptions} />
      </div>
      <div>
        <label className={LABEL}>Pré-contrato (formulário recebido)</label>
        <p className="mb-1 text-xs text-muted">
          Vincule a resposta do formulário de pré-contrato preenchida pela cliente (opcional).
        </p>
        <FormResponsePicker value={formResponse} onChange={onFormResponseChange} />
      </div>
    </BlockCard>
  );
}
