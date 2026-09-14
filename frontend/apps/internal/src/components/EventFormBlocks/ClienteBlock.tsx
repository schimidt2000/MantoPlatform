import { LABEL, AlertasDoCampo, BlockCard, DoFormulario } from "./shared";
import { ClientPicker } from "../ClientPicker";
import { FormResponsePicker, type SelectedFormResponse } from "../FormResponsePicker";
import type { ClientLinkInput } from "../../lib/eventCreate";
import type { QuickCreateClientInput } from "../../lib/clientes";
import type { AlertaFormulario } from "../../lib/formulariosAdmin";

export interface ClienteBlockProps {
  clients: (ClientLinkInput & { name: string })[];
  onClientsChange: (next: (ClientLinkInput & { name: string })[]) => void;
  relationOptions: string[];
  formResponse: SelectedFormResponse | null;
  onFormResponseChange: (next: SelectedFormResponse | null) => void;
  /** Feature 298: a cliente veio do formulário (marca "do formulário"). */
  doFormulario?: ReadonlySet<string>;
  /** Feature 298: cliente sugerida pelo telefone, para conferir. */
  alertas?: AlertaFormulario[];
  /** Feature 298: sem ficha, o cadastro rápido abre sozinho com os dados do formulário. */
  cadastroRapidoInicial?: Partial<QuickCreateClientInput>;
}

/** Bloco 1 — Cliente e pré-contrato (feature 184). */
export function ClienteBlock({
  clients,
  onClientsChange,
  relationOptions,
  formResponse,
  onFormResponseChange,
  doFormulario,
  alertas,
  cadastroRapidoInicial,
}: ClienteBlockProps) {
  return (
    <BlockCard title="Cliente e pré-contrato" id="bloco-cliente">
      <div>
        <label className={LABEL}>
          Clientes associados <DoFormulario campo="clients" doFormulario={doFormulario} />
        </label>
        <ClientPicker
          value={clients}
          onChange={onClientsChange}
          relationOptions={relationOptions}
          cadastroRapidoInicial={cadastroRapidoInicial}
        />
        <AlertasDoCampo campo="clients" alertas={alertas} />
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
