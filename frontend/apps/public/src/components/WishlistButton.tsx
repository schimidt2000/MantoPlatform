import { useEffect, useState } from "react";
import { wishlist } from "../lib/wishlist";

interface WishlistButtonProps {
  slug: string;
  name: string;
  cover: string | null;
  /** "tema" (default) | "personagem" (feature 185) — distingue o item na lista de interesse. */
  kind?: "tema" | "personagem";
  /** Slug do Tema pai — obrigatório quando `kind === "personagem"`. */
  parentSlug?: string;
  /** Botão circular só com ícone (sobreposto ao card) em vez do botão de texto completo. */
  compact?: boolean;
}

/** Botão de favoritar — usado no card do produto, no card de Personagem e no detalhe (feature 140/161/185). */
export function WishlistButton({
  slug,
  name,
  cover,
  kind = "tema",
  parentSlug,
  compact = false,
}: WishlistButtonProps) {
  const [added, setAdded] = useState(false);

  useEffect(() => {
    setAdded(wishlist.has(slug));
  }, [slug]);

  function handleClick(event: React.MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    wishlist.toggle({ slug, name, cover: cover ?? "", kind, parentSlug });
    setAdded(wishlist.has(slug));
  }

  if (compact) {
    return (
      <button
        type="button"
        onClick={handleClick}
        aria-label={added ? "Remover da lista de desejos" : "Adicionar à lista de desejos"}
        aria-pressed={added}
        className={`flex h-9 w-9 items-center justify-center rounded-full border text-base shadow-sm transition-colors ${
          added
            ? "border-accent bg-accent text-white"
            : "border-line bg-panel text-ink hover:border-accent"
        }`}
      >
        {added ? "♥" : "♡"}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-pressed={added}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-sm font-semibold transition-colors ${
        added
          ? "border-accent bg-accent text-white"
          : "border-line bg-panel text-ink hover:border-accent"
      }`}
    >
      {added ? "✓ Na lista" : "♡ Adicionar à lista"}
    </button>
  );
}
