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
  /**
   * URL de um arquivo já salvo no servidor (feature 180) — mostrado como preview/link antes de
   * qualquer nova seleção. `assetUrl()` já resolvido pelo chamador (o componente não conhece a
   * origem da API).
   */
  existingUrl?: string | null;
  /** Rótulo do arquivo já salvo (ex.: nome do arquivo), exibido ao lado do preview. */
  existingLabel?: string;
  /** Chamado ao remover o arquivo já salvo (sem escolher um novo) — omitido esconde o botão. */
  onRemoveExisting?: () => void;
  /** Estado de carregamento da remoção do arquivo já salvo. */
  removingExisting?: boolean;
}

/**
 * Teto para a cópia em memória do arquivo escolhido (ver `snapshotFile`).
 *
 * Cobre com folga todas as superfícies de foto/documento (8 a 20 MB). Acima disso só existe o
 * Acervo 3D (50 MB), que é upload de desktop: lá o arquivo não é reescrito por sincronização de
 * nuvem no meio do formulário, e segurar 50 MB em RAM custaria mais do que resolve.
 */
const SNAPSHOT_MAX_BYTES = 24 * 1024 * 1024;

function formatMb(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
}

/**
 * Cópia do arquivo em memória, desligada do disco.
 *
 * O `<input type="file">` guarda só uma REFERÊNCIA. O Chrome anota tamanho e data de modificação
 * no momento da escolha e reabre o arquivo na hora do envio — se qualquer um dos dois mudou, ele
 * aborta com `ERR_UPLOAD_FILE_CHANGED` sem mandar um byte, e a pessoa recebe uma tela de erro do
 * navegador em vez do formulário. Num formulário longo preenchido no celular isso acontece de
 * verdade: o Google Fotos/Drive reescreve o arquivo temporário que entregou, o iOS descarta a
 * conversão HEIC→JPEG sob pressão de memória, a pessoa corta ou gira a foto depois de anexar.
 *
 * Lendo os bytes agora, o `FormData` passa a apontar para memória e o navegador nunca mais volta
 * ao disco — o erro deixa de ser possível. De quebra, um arquivo já ilegível falha AQUI, com a
 * seleção fresca na cabeça de quem escolheu, e não vinte minutos depois no envio.
 */
async function snapshotFile(file: File): Promise<File> {
  const bytes = await file.arrayBuffer();
  return new File([bytes], file.name, { type: file.type, lastModified: file.lastModified });
}

/**
 * Campo de upload de arquivo com preview de imagem — primeiro componente compartilhado de
 * upload do design system (feature 162, `research.md` §3). Além do `accept` nativo, valida
 * localmente só o que dá para checar sem enviar nada: o tamanho máximo e a legibilidade do
 * arquivo. O resto da validação de negócio continua sendo do backend, refletida via `error`.
 */
export function FileUpload({
  label,
  accept,
  maxSizeBytes,
  required = false,
  error,
  onChange,
  existingUrl,
  existingLabel,
  onRemoveExisting,
  removingExisting = false,
}: FileUploadProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  /** Problema detectado na própria escolha (tamanho/leitura) — soma-se ao `error` do chamador. */
  const [localError, setLocalError] = useState<string | null>(null);

  const maxSizeMb = Math.round(maxSizeBytes / (1024 * 1024));
  const shownError = error ?? localError ?? undefined;

  function replacePreview(file: File | null) {
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return file && file.type.startsWith("image/") ? URL.createObjectURL(file) : null;
    });
  }

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0] ?? null;
    setLocalError(null);
    setFileName(picked?.name ?? null);

    if (!picked) {
      replacePreview(null);
      onChange(null);
      return;
    }

    // Rejeitar aqui evita subir o arquivo inteiro para o backend recusar no fim — no celular
    // isso é a diferença entre um aviso imediato e minutos de upload jogados fora.
    if (picked.size > maxSizeBytes) {
      replacePreview(null);
      setLocalError(`Arquivo de ${formatMb(picked.size)} — o limite é ${maxSizeMb} MB.`);
      onChange(null);
      return;
    }

    // Grande demais para copiar (hoje só o Acervo 3D): segue com a referência de disco de sempre.
    if (picked.size > SNAPSHOT_MAX_BYTES) {
      replacePreview(picked);
      onChange(picked);
      return;
    }

    try {
      const stable = await snapshotFile(picked);
      replacePreview(stable);
      onChange(stable);
    } catch {
      replacePreview(null);
      setLocalError(
        "Não foi possível ler este arquivo. Se ele veio do Google Fotos ou do Drive, " +
          "salve na galeria do aparelho e escolha de novo.",
      );
      onChange(null);
    }
  }

  function handleClear() {
    if (inputRef.current) inputRef.current.value = "";
    setFileName(null);
    setLocalError(null);
    replacePreview(null);
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
        aria-invalid={Boolean(shownError)}
      />
      <div
        className={cn(
          "flex min-h-11 items-center gap-3 rounded-md border border-line bg-panel p-2",
          shownError && "border-red ring-2 ring-red/30",
        )}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="" className="h-11 w-11 shrink-0 rounded-sm object-cover" />
        ) : !fileName && existingUrl && !existingUrl.toLowerCase().endsWith(".pdf") ? (
          <img src={existingUrl} alt="" className="h-11 w-11 shrink-0 rounded-sm object-cover" />
        ) : null}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => inputRef.current?.click()}
          // `min-h-[44px]` sobrepõe o h-9 do tamanho `sm`: este é o único controle de toque do
          // componente, e o Portal do Artista é mobile-only (Princípio VIII, alvo ≥44px). No
          // desktop o botão só cresce 8px, sem quebrar layout.
          className="min-h-[44px] shrink-0"
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          {fileName || existingUrl ? "Trocar" : "Escolher arquivo"}
        </Button>
        <span className="min-w-0 flex-1 truncate text-sm text-ink">
          {fileName ??
            (existingUrl ? (existingLabel ?? "Arquivo já enviado") : `Nenhum arquivo (máx. ${maxSizeMb} MB)`)}
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
        {!fileName && existingUrl && onRemoveExisting && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-label="Remover arquivo enviado"
            loading={removingExisting}
            onClick={onRemoveExisting}
            className="shrink-0"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        )}
      </div>
      {shownError && (
        <p className="mt-1 text-sm text-red" role="alert">
          {shownError}
        </p>
      )}
    </div>
  );
}
