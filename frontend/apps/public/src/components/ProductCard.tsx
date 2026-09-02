import { Link } from "react-router-dom";
import { assetSrcSet, assetUrl } from "@manto/api-client";
import type { CatalogItemSummary } from "../lib/catalogo";
import { WishlistButton } from "./WishlistButton";

interface ProductCardProps {
  item: CatalogItemSummary;
  /** Tamanho maior de foto/nome — usado na grade de uma categoria (feature 133/140). */
  large?: boolean;
}

/**
 * `sizes` espelha a grade REAL de cada uso (feature 270): grade geral/relacionados são
 * `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4`; a grade de categoria (`large`) é
 * `grid-cols-2 sm:grid-cols-3` dentro de `max-w-[1180px]`. É por este atributo que o navegador
 * escolhe entre as variantes de 320/480/640 — sem ele, assume 100vw e pede sempre a maior.
 * No celular a coluna é `calc(50vw - 32px)` (padding 24px de cada lado + gap 16px), não `50vw`:
 * a diferença decide se um aparelho de 375px com DPR 2 fica no 320 (311px pedidos) ou sobe.
 */
const SIZES_GRADE = "(min-width: 1024px) 25vw, (min-width: 640px) 33vw, calc(50vw - 32px)";
const SIZES_CATEGORIA = "(min-width: 640px) 33vw, calc(50vw - 34px)";
const LARGURAS_CARD = [320, 480, 640] as const;

/** Card de produto reutilizado pela grade geral, grade de categoria e relacionados do detalhe. */
export function ProductCard({ item, large = false }: ProductCardProps) {
  return (
    <div className="relative">
      <Link
        to={`/${item.slug}`}
        className="block overflow-hidden rounded-lg bg-panel shadow-sm transition-transform hover:-translate-y-1 hover:shadow-lg"
      >
        <div className="aspect-[4/5] overflow-hidden bg-bg-alt">
          {item.cover_image_url && (
            <img
              src={assetUrl(item.cover_image_url, { largura: 640 })}
              srcSet={assetSrcSet(item.cover_image_url, LARGURAS_CARD)}
              sizes={large ? SIZES_CATEGORIA : SIZES_GRADE}
              alt={item.name}
              loading="lazy"
              className="h-full w-full object-cover"
            />
          )}
        </div>
        <div className={large ? "p-5" : "p-4"}>
          <div className={`font-display font-medium text-ink ${large ? "mb-2 text-xl" : "mb-2 text-base"}`}>
            {item.name}
          </div>
          {!large && item.categories.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {item.categories.slice(0, 3).map((name) => (
                <span
                  key={name}
                  className="rounded-full bg-accent-soft px-2.5 py-0.5 text-[10.5px] font-semibold text-accent-dark"
                >
                  {name}
                </span>
              ))}
            </div>
          )}
        </div>
      </Link>
      <div className="absolute right-2.5 top-2.5">
        <WishlistButton
          slug={item.slug}
          name={item.name}
          cover={item.cover_image_url}
          compact
        />
      </div>
    </div>
  );
}
