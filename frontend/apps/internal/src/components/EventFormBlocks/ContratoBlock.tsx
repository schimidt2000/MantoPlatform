import type { ReactNode } from "react";
import { FileUpload } from "@manto/ui";
import { BlockCard } from "./shared";

export interface ContratoBlockProps {
  contractFile: File | null;
  onContractFileChange: (file: File | null) => void;
  contractSigned: boolean;
  onContractSignedChange: (signed: boolean) => void;
  /** Resumo dos contratos já salvos (feature 184, edição) — gestão completa (assinado/excluir)
   * continua na tela de detalhe do evento. */
  existingNote?: ReactNode;
}

/** Bloco 6 — Contrato, opcional (feature 184). */
export function ContratoBlock({
  contractFile,
  onContractFileChange,
  contractSigned,
  onContractSignedChange,
  existingNote,
}: ContratoBlockProps) {
  return (
    <BlockCard title="Contrato (opcional)" id="bloco-contrato">
      {existingNote}
      <FileUpload
        label="Arquivo do contrato"
        accept="application/pdf,image/png,image/jpeg"
        maxSizeBytes={20 * 1024 * 1024}
        onChange={onContractFileChange}
      />
      {contractFile && (
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={contractSigned}
            onChange={(e) => onContractSignedChange(e.target.checked)}
          />
          Contrato já assinado
        </label>
      )}
    </BlockCard>
  );
}
