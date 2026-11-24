import { assetUrl } from "@manto/api-client";
import { Foto } from "@manto/ui";

interface GaleriaDoItemProps {
  nome: string;
  fotos: { id: number; url: string }[];
  onAbrir: (url: string, nome: string) => void;
}

/**
 * As fotos da galeria do item, para comparar com os recortes que a leitura propôs (FR-013). Cada
 * uma abre no visualizador do sistema: no celular em modo app, "outra aba" é uma janela sem saída.
 */
export function GaleriaDoItem({ nome, fotos, onAbrir }: GaleriaDoItemProps) {
  if (fotos.length === 0) {
    return <p className="text-sm text-muted">Nenhuma foto na galeria deste item.</p>;
  }
  return (
    <ul className="grid grid-cols-5 gap-1.5 sm:grid-cols-8 lg:grid-cols-10" aria-label={`Fotos de ${nome}`}>
      {fotos.map((foto, indice) => (
        <li key={foto.id}>
          <button
            type="button"
            onClick={() => onAbrir(foto.url, `${nome} — foto ${indice + 1}`)}
            aria-label={`Ver a foto ${indice + 1} de ${nome}`}
            className="block aspect-square w-full overflow-hidden rounded-md border border-line bg-surface-2"
          >
            <Foto
              src={assetUrl(foto.url)}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
              fallback={<span className="flex h-full items-center justify-center text-[11px] text-muted">Sem foto</span>}
            />
          </button>
        </li>
      ))}
    </ul>
  );
}
