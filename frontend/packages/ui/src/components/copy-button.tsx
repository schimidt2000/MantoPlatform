import { useState } from "react";

export interface CopyButtonProps {
  value: string;
  label: string;
}

/**
 * Botão compacto de cópia rápida (Princípio V — nunca fica "morto" ao clique): troca para
 * "✓ Copiado" por ~1,8 s e anuncia o resultado por `aria-live` para leitores de tela.
 * Promovido de `PagamentosPage.tsx` (feature 189) para fonte única (Princípio I).
 */
function CopyButton({ value, label }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // Clipboard bloqueado (contexto não seguro): o texto continua visível para seleção manual.
      return;
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <>
      <button
        type="button"
        onClick={copy}
        title={label}
        aria-label={label}
        className="shrink-0 rounded-md border border-line px-1 py-0.5 text-[10px] leading-none text-muted transition-colors hover:bg-surface-2 hover:text-ink"
      >
        {copied ? "✓" : "⧉"}
      </button>
      <span aria-live="polite" className="sr-only">
        {copied ? `${label}: copiado` : ""}
      </span>
    </>
  );
}

export { CopyButton };
