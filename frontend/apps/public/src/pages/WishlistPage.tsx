import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { useCatalogList } from "../lib/catalogo";
import { wishlist, type WishlistItem } from "../lib/wishlist";

export function WishlistPage() {
  const [items, setItems] = useState<WishlistItem[]>([]);
  const { data } = useCatalogList();

  useEffect(() => {
    setItems(wishlist.getAll());
  }, []);

  function handleRemove(slug: string) {
    setItems(wishlist.remove(slug));
  }

  function handleSend() {
    const number = data?.whatsapp_number;
    if (!number) return;
    const url = wishlist.whatsappUrl(number);
    if (url) window.open(url, "_blank", "noopener");
  }

  return (
    <div className="pb-24">
      <div className="border-b border-line px-6 py-5">
        <div className="mx-auto max-w-[1180px]">
          <Link to="/" className="text-[13.5px] font-semibold text-muted hover:text-accent">
            ← Voltar ao catálogo
          </Link>
        </div>
      </div>

      <header className="px-6 py-9 text-center">
        <div className="mx-auto max-w-[1180px]">
          <div className="text-xs font-bold uppercase tracking-[0.16em] text-gold">
            ✦ Manto Produções
          </div>
          <h1 className="mt-2 font-display text-3xl font-medium text-ink sm:text-4xl">
            Sua lista de desejos
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            Reveja os personagens escolhidos e envie a lista pra gente pelo WhatsApp.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-[640px] px-6">
        {items.length === 0 ? (
          <div className="py-16 text-center text-muted">
            <div className="mb-3 text-4xl">🤍</div>
            <div>
              Sua lista está vazia. Volte ao catálogo e adicione os personagens que você
              gostou.
            </div>
          </div>
        ) : (
          <div>
            {items.map((item) => (
              <div
                key={item.slug}
                className="mb-3 flex items-center gap-3.5 rounded-lg bg-panel p-3.5 shadow-sm"
              >
                <div className="h-16 w-16 flex-none overflow-hidden rounded-md bg-bg-alt">
                  {item.cover && (
                    <img
                      src={assetUrl(item.cover)}
                      alt={item.name}
                      loading="lazy"
                      className="h-full w-full object-cover"
                    />
                  )}
                </div>
                <Link to={`/${item.slug}`} className="flex-1 font-display text-base font-medium text-ink">
                  {item.name}
                </Link>
                <button
                  type="button"
                  onClick={() => handleRemove(item.slug)}
                  aria-label="Remover da lista"
                  className="p-1.5 text-xl leading-none text-muted hover:text-red"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={handleSend}
            disabled={items.length === 0}
            className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:translate-y-0"
          >
            📲 Enviar para o vendedor
          </button>
        </div>
      </main>
    </div>
  );
}
