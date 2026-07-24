import { useState } from "react";
import { assetUrl } from "@manto/api-client";
import type { CatalogCharacter } from "../lib/catalogo";
import { WishlistButton } from "./WishlistButton";

interface CharacterCardProps {
  character: CatalogCharacter;
  temaSlug: string;
  highlighted?: boolean;
}

/**
 * Card de um Personagem filho de um Tema (feature 185, FR-004) — foto ou preview de vídeo mudo,
 * nome, e ação de adicionar à lista de interesse independente do Tema completo.
 */
export function CharacterCard({ character, temaSlug, highlighted = false }: CharacterCardProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopyLink() {
    const url = `${window.location.origin}/${temaSlug}?personagem=${character.slug}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // clipboard indisponível — ignora, o link continua disponível manualmente
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div
      id={`personagem-${character.slug}`}
      className={`overflow-hidden rounded-xl border bg-panel shadow-sm transition-shadow hover:shadow-md ${
        highlighted ? "border-gold ring-2 ring-gold" : "border-line"
      }`}
    >
      <div className="aspect-square overflow-hidden bg-bg-alt">
        {character.photo_url ? (
          <img
            src={assetUrl(character.photo_url)}
            alt={character.name}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : character.video_url ? (
          <div className="flex h-full w-full items-center justify-center bg-ink/80 text-3xl text-white">
            ▶
          </div>
        ) : (
          <div className="flex h-full w-full items-center justify-center text-3xl">🎭</div>
        )}
      </div>
      <div className="space-y-2 p-3">
        <h3 className="text-balance font-display text-base font-medium text-ink">
          {character.name}
        </h3>
        <div className="flex flex-wrap gap-1.5">
          <WishlistButton
            slug={character.slug}
            name={character.name}
            cover={character.photo_url}
            kind="personagem"
            parentSlug={temaSlug}
          />
          <button
            type="button"
            onClick={handleCopyLink}
            aria-label="Copiar link do personagem"
            className="inline-flex h-11 w-11 flex-none items-center justify-center rounded-full border border-line text-sm font-semibold text-accent-dark hover:border-accent"
          >
            {copied ? "✅" : "🔗"}
          </button>
        </div>
      </div>
    </div>
  );
}
