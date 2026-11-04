import { Megaphone } from "lucide-react";
import type { AnuncioDaConversa } from "../../lib/conversas";

/**
 * De onde a cliente veio (feature 334, FR-008): o anúncio — ou a publicação — mais recente da
 * conversa, numa linha fina sob o cabeçalho. A campanha só aparece depois que a Meta respondeu; o
 * título abre o anúncio quando a Meta mandou o link.
 */
export function OrigemDaConversa({ anuncio }: { anuncio: AnuncioDaConversa }) {
  const publicacao = anuncio.tipo === "publicacao";
  const link = anuncio.link?.startsWith("https://") ? anuncio.link : null;
  const titulo = anuncio.titulo ? `“${anuncio.titulo}”` : null;
  const inteiro = [titulo, anuncio.campanha].filter(Boolean).join(" · ");
  return (
    <p className="flex min-w-0 items-center gap-1.5 border-b border-line bg-panel px-3 py-1.5 text-xs text-muted">
      <Megaphone className="h-3.5 w-3.5 shrink-0" aria-hidden />
      {/* No celular a linha corta: o texto inteiro fica no title. */}
      <span className="min-w-0 truncate" title={inteiro || undefined}>
        {titulo ? (publicacao ? "Veio da publicação " : "Veio do anúncio ") : publicacao ? "Veio de uma publicação" : "Veio de um anúncio"}
        {titulo && link ? (
          <a href={link} target="_blank" rel="noopener noreferrer" className="text-ink underline-offset-2 hover:underline">
            {titulo}
          </a>
        ) : (
          titulo && <span className="text-ink">{titulo}</span>
        )}
        {anuncio.campanha ? ` · ${anuncio.campanha}` : null}
      </span>
    </p>
  );
}
