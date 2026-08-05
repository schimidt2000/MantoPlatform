import { useEffect, useRef, useState } from "react";
import { Bold, Italic, RemoveFormatting } from "lucide-react";

export interface RichTextEditorProps {
  /** HTML atual (o que está persistido em `short_description_html`). */
  value: string;
  onChange: (html: string) => void;
  ariaLabel?: string;
}

/**
 * Editor rich-text mínimo para a descrição do catálogo: negrito, itálico e Enter=parágrafo,
 * editando o texto formatado direto (nada de `<strong>` na mão). Sem dependência nova —
 * `contentEditable` + `document.execCommand` (deprecado, mas universal para bold/italic; o
 * acervo atual já usa `<b>`, então a saída dos browsers é coerente com os dados).
 *
 * O valor continua sendo HTML — zero migração de dados — e o backend sanitiza com nh3 na
 * gravação (`catalog_ops._sanitize_description`), então o que o editor emite é só
 * conveniência, nunca fronteira de segurança.
 *
 * Cuidados de implementação:
 * - `innerHTML` só é (re)atribuído quando o editor NÃO tem foco — reescrever durante a
 *   digitação faria o cursor saltar para o início.
 * - Colar insere SEMPRE texto puro (`insertText`) — colar do Word/site traria uma sopa de
 *   spans que a sanitização descartaria de qualquer forma.
 * - `onMouseDown` com `preventDefault` nos botões da toolbar preserva a seleção do texto.
 */
export function RichTextEditor({ value, onChange, ariaLabel }: RichTextEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const [activeMarks, setActiveMarks] = useState({ bold: false, italic: false });

  // Enter deve gerar <p> (o acervo e o CSS público estilizam parágrafos); sem isto o
  // Chrome envolve linhas em <div>. Nem todo engine respeita — a vitrine também estiliza
  // div como fallback.
  useEffect(() => {
    document.execCommand("defaultParagraphSeparator", false, "p");
  }, []);

  // Sincroniza o HTML externo → editor (carregamento da página / reset do form).
  useEffect(() => {
    const el = editorRef.current;
    if (!el || document.activeElement === el) return;
    if (el.innerHTML !== value) el.innerHTML = value;
  }, [value]);

  // Estado ativo dos botões B/I acompanha a posição do cursor.
  useEffect(() => {
    function syncMarks() {
      const el = editorRef.current;
      if (!el || document.activeElement !== el) return;
      setActiveMarks({
        bold: document.queryCommandState("bold"),
        italic: document.queryCommandState("italic"),
      });
    }
    document.addEventListener("selectionchange", syncMarks);
    return () => document.removeEventListener("selectionchange", syncMarks);
  }, []);

  function exec(command: "bold" | "italic" | "removeFormat") {
    editorRef.current?.focus();
    document.execCommand(command);
    if (editorRef.current) onChange(editorRef.current.innerHTML);
  }

  const toolbarButton = (active: boolean) =>
    `rounded p-1.5 transition-colors ${
      active ? "bg-accent-soft text-accent-dark" : "text-muted hover:bg-surface-2 hover:text-ink"
    }`;

  return (
    <div className="rounded-md border border-line bg-panel">
      <div className="flex items-center gap-0.5 border-b border-line px-1.5 py-1" role="toolbar">
        <button
          type="button"
          aria-label="Negrito (Ctrl+B)"
          aria-pressed={activeMarks.bold}
          className={toolbarButton(activeMarks.bold)}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => exec("bold")}
        >
          <Bold className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label="Itálico (Ctrl+I)"
          aria-pressed={activeMarks.italic}
          className={toolbarButton(activeMarks.italic)}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => exec("italic")}
        >
          <Italic className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label="Limpar formatação"
          className={toolbarButton(false)}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => exec("removeFormat")}
        >
          <RemoveFormatting className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
      <div
        ref={editorRef}
        contentEditable
        role="textbox"
        aria-multiline="true"
        aria-label={ariaLabel}
        className="min-h-20 w-full p-2 text-sm text-ink outline-none [&_b]:font-semibold [&_strong]:font-semibold [&_i]:italic [&_em]:italic"
        onInput={() => {
          if (editorRef.current) onChange(editorRef.current.innerHTML);
        }}
        onPaste={(e) => {
          e.preventDefault();
          document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
        }}
      />
    </div>
  );
}
