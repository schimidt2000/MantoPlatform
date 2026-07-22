import { useId, useRef, useState, type ChangeEvent } from "react";
import { Upload, X } from "lucide-react";
import { cn } from "../lib/cn";
import { Button } from "./button";

export interface FileUploadProps {
  /** Rótulo exibido acima do campo. */
  label: string;
  /** MIME types aceitos (atributo `accept` nativo), ex.: `"image/jpeg,image/png,image/webp"`. */
  accept: string;
  /** Tamanho máximo em bytes — mensagem de ajuda mostra o valor em MB. */
  maxSizeBytes: number;
  /** Se `true`, exibe indicação visual de campo obrigatório. */
  required?: boolean;
  /** Mensagem de erro (validação client-side ou vinda da API) — realça a borda em vermelho. */
  error?: string;
  /** Chamado com o arquivo escolhido, ou `null` ao remover a seleção. */
  onChange: (file: File | null) => void;
}

/**
 * Campo de upload de arquivo com preview de imagem — primeiro componente compartilhado de
 * upload do design system (feature 162, `research.md` §3). Não valida tipo/tamanho por conta
 * própria além do atributo `accept` nativo do input — a validação de negócio (extensão exata,
 * tamanho máximo) é responsabilidade do backend/schema, aqui só refletida via `error`.
 */
export function FileUpload({
  label,
  accept,
  maxSizeBytes,
  required = false,
  error,
  onChange,
}: FileUploadProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const maxSizeMb = Math.round(maxSizeBytes / (1024 * 1024));

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setFileName(file?.name ?? null);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return file && file.type.startsWith("image/") ? URL.createObjectURL(file) : null;
    });
    onChange(file);
  }

  function handleClear() {
    if (inputRef.current) inputRef.current.value = "";
    setFileName(null);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    onChange(null);
  }

  return (
    <div>
      <label htmlFor={inputId} className="mb-1 block text-sm text-muted">
        {label}
        {required && <span className="text-red"> *</span>}
      </label>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={accept}
        onChange={handleChange}
        className="sr-only"
        aria-invalid={Boolean(error)}
      />
      <div
        className={cn(
          "flex min-h-11 items-center gap-3 rounded-md border border-line bg-panel p-2",
          error && "border-red ring-2 ring-red/30",
        )}
      >
        {previewUrl ? (
          <img
            src={previewUrl}
            alt=""
            className="h-11 w-11 shrink-0 rounded-sm object-cover"
          />
        ) : null}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => inputRef.current?.click()}
          className="shrink-0"
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          {fileName ? "Trocar" : "Escolher arquivo"}
        </Button>
        <span className="min-w-0 flex-1 truncate text-sm text-ink">
          {fileName ?? `Nenhum arquivo (máx. ${maxSizeMb} MB)`}
        </span>
        {fileName && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-label="Remover arquivo"
            onClick={handleClear}
            className="shrink-0"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        )}
      </div>
      {error && (
        <p className="mt-1 text-sm text-red" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
