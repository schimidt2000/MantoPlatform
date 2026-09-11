import type { ReactNode } from "react";
import { useFormContext } from "react-hook-form";
import { MoneyInput } from "@manto/money";
import { FileUpload } from "@manto/ui";
import type { EventFormValues } from "../../lib/eventFormSchema";
import type { AlertaFormulario } from "../../lib/formulariosAdmin";
import { GoogleAddressInput } from "../GoogleAddressInput";
import {
  FIELD,
  FIELD_ERROR,
  LABEL,
  HELP,
  AlertasDoCampo,
  DoFormulario,
  FieldError,
  BlockCard,
} from "./shared";

export interface DadosEventoBlockProps {
  /** Feature 298: campos que vieram do formulário da cliente (marca "do formulário"). */
  doFormulario?: ReadonlySet<string>;
  /** Feature 298: o que não entrou do formulário, com o texto da cliente, mostrado no campo. */
  alertas?: AlertaFormulario[];
  /**
   * Feature 298: data suspeita vinda do formulário. A caixa "A data está certa" dispensa a
   * conferência — o Salvar nunca fica desabilitado por causa dela.
   */
  confirmacaoDaData?: { marcada: boolean; onChange: (marcada: boolean) => void };
  hasReembolso: boolean;
  onHasReembolsoChange: (value: boolean) => void;
  reembolsoDescription: string;
  onReembolsoDescriptionChange: (value: string) => void;
  reembolsoAmount: number;
  onReembolsoAmountChange: (value: number) => void;
  reembolsoInvoiceFile: File | null;
  onReembolsoInvoiceFileChange: (file: File | null) => void;
  /** Reembolsos já salvos (feature 184, edição) — cobrar/excluir continua na tela de detalhe. */
  existingReembolsoNote?: ReactNode;
}

/** Bloco 2 — Dados do evento (feature 184). */
export function DadosEventoBlock({
  hasReembolso,
  onHasReembolsoChange,
  reembolsoDescription,
  onReembolsoDescriptionChange,
  reembolsoAmount,
  onReembolsoAmountChange,
  reembolsoInvoiceFile,
  onReembolsoInvoiceFileChange,
  existingReembolsoNote,
  doFormulario,
  alertas,
  confirmacaoDaData,
}: DadosEventoBlockProps) {
  const {
    register,
    watch,
    setValue,
    formState: { errors },
  } = useFormContext<EventFormValues>();

  const eventType = watch("event_type");
  const start = watch("start");
  const end = watch("end");
  const overnight = Boolean(start && end && end < start && end !== start);

  return (
    <BlockCard title="Dados do evento" id="bloco-dados-evento">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL} htmlFor="date">
            Data * <DoFormulario campo="date" doFormulario={doFormulario} />
          </label>
          <input
            id="date"
            type="date"
            className={errors.date ? FIELD_ERROR : FIELD}
            {...register("date")}
          />
          <FieldError message={errors.date?.message} />
          <AlertasDoCampo campo="date" alertas={alertas} />
          {confirmacaoDaData && (
            <label className="mt-1.5 flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                className="h-5 w-5"
                checked={confirmacaoDaData.marcada}
                onChange={(e) => confirmacaoDaData.onChange(e.target.checked)}
              />
              A data está certa (conferi com a cliente)
            </label>
          )}
        </div>
        <div>
          <label className={LABEL} htmlFor="event_type">
            Tipo <DoFormulario campo="event_type" doFormulario={doFormulario} />
          </label>
          <select id="event_type" className={FIELD} {...register("event_type")}>
            <option value="">— Selecionar —</option>
            <option value="SHOW">SHOW — Show com som</option>
            <option value="CORP">CORP — Corporativo</option>
            <option value="R&I">R&amp;I — Receptivo e Interativo</option>
            <option value="VM">VM — Visita Mágica</option>
          </select>
          <AlertasDoCampo campo="event_type" alertas={alertas} />
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL} htmlFor="start">
            Horário de início * <DoFormulario campo="start" doFormulario={doFormulario} />
          </label>
          <input
            id="start"
            type="time"
            className={errors.start ? FIELD_ERROR : FIELD}
            {...register("start")}
          />
          <FieldError message={errors.start?.message} />
          <AlertasDoCampo campo="start" alertas={alertas} />
        </div>
        <div>
          <label className={LABEL} htmlFor="end">
            Horário de fim * <DoFormulario campo="end" doFormulario={doFormulario} />
          </label>
          <input
            id="end"
            type="time"
            className={errors.end ? FIELD_ERROR : FIELD}
            {...register("end")}
          />
          <FieldError message={errors.end?.message} />
          {!errors.end && overnight && (
            <p className={HELP}>↪ termina no dia seguinte</p>
          )}
          <AlertasDoCampo campo="end" alertas={alertas} />
        </div>
      </div>
      <div>
        <label className={LABEL} htmlFor="location">
          Local/Endereço do evento <DoFormulario campo="location" doFormulario={doFormulario} />
        </label>
        {/* Autocomplete do Google Places (feature 195, Princípio X.3) — evita erro de logística e
            cálculo de distância impreciso. `setValue` no lugar do `register` porque o valor vem do
            componente, não de um evento nativo de input. */}
        <GoogleAddressInput
          id="location"
          aria-label="Local/Endereço do evento"
          value={watch("location") ?? ""}
          onChange={(value) => setValue("location", value, { shouldDirty: true })}
        />
        <p className={HELP}>
          Comece a digitar e escolha uma sugestão do Google Maps para gravar o endereço completo.
        </p>
        <AlertasDoCampo campo="location" alertas={alertas} />
      </div>
      <div>
        <label className={LABEL} htmlFor="description">
          Descrição do evento
        </label>
        <textarea id="description" rows={3} className={FIELD} {...register("description")} />
        <p className={HELP}>Aparece na descrição do Google Agenda e na página do evento.</p>
      </div>

      {eventType === "SHOW" ? (
        <div>
          <label className="flex items-center gap-2 text-sm text-ink opacity-70">
            <input type="checkbox" className="h-5 w-5" checked disabled readOnly />
            Sim, adicionar ensaio ao evento
          </label>
          <p className={HELP}>Eventos SHOW sempre geram ensaio automaticamente.</p>
        </div>
      ) : (
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" className="h-5 w-5" {...register("needs_rehearsal")} />
          Sim, adicionar ensaio ao evento
        </label>
      )}

      <div className="border-t border-line pt-3">
        {existingReembolsoNote}
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={hasReembolso}
            onChange={(e) => onHasReembolsoChange(e.target.checked)}
          />
          Este evento terá reembolso de despesas da cliente? (bagagem, alimentação etc.)
        </label>
        {hasReembolso && (
          <div className="mt-3 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL}>Descrição</label>
                <input
                  className={FIELD}
                  placeholder="Ex.: Bagagem extra"
                  value={reembolsoDescription}
                  onChange={(e) => onReembolsoDescriptionChange(e.target.value)}
                />
              </div>
              <div>
                <label className={LABEL}>Valor a cobrar (R$)</label>
                <MoneyInput
                  className={FIELD}
                  value={reembolsoAmount}
                  onValueChange={onReembolsoAmountChange}
                />
              </div>
            </div>
            <FileUpload
              label="Nota fiscal do gasto (opcional)"
              accept="application/pdf,image/png,image/jpeg"
              maxSizeBytes={10 * 1024 * 1024}
              onChange={onReembolsoInvoiceFileChange}
            />
            {reembolsoInvoiceFile && (
              <p className={HELP}>Arquivo selecionado: {reembolsoInvoiceFile.name}</p>
            )}
            <p className={HELP}>Pode deixar em branco e adicionar depois, direto na página do evento.</p>
          </div>
        )}
      </div>
    </BlockCard>
  );
}
