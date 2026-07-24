import type { CatalogCharacter } from "../lib/catalogo";
import { CharacterCard } from "./CharacterCard";

interface CharacterGridProps {
  characters: CatalogCharacter[];
  temaSlug: string;
  highlightedSlug?: string | null;
}

/**
 * Seção "Personagens deste Tema / Elenco Individual" (feature 185, FR-004) — não renderiza nada
 * se o Tema não tiver Personagens ativos (Edge Case da spec: sem espaço vazio/quebrado).
 */
export function CharacterGrid({ characters, temaSlug, highlightedSlug }: CharacterGridProps) {
  if (characters.length === 0) {
    return null;
  }

  return (
    <div className="mt-16 border-t border-line pt-10">
      <h2 className="mb-1 text-balance font-display text-2xl font-medium text-ink sm:text-3xl">
        ✦ Elenco Individual
      </h2>
      <p className="mb-5 text-sm text-muted">
        Cada personagem também pode ser contratado separadamente do pacote completo.
      </p>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {characters.map((character) => (
          <CharacterCard
            key={character.id}
            character={character}
            temaSlug={temaSlug}
            highlighted={character.slug === highlightedSlug}
          />
        ))}
      </div>
    </div>
  );
}
