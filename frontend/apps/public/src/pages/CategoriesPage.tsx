import { Link } from "react-router-dom";
import { Skeleton } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { useCategories } from "../lib/catalogo";

export function CategoriesPage() {
  const { data, isLoading, isError } = useCategories();

  return (
    <div className="pb-24">
      <header className="border-b border-line bg-gradient-to-b from-bg-alt to-bg px-6 py-14 text-center">
        <div className="mx-auto max-w-[1180px]">
          <div className="text-xs font-bold uppercase tracking-[0.16em] text-gold">
            ✦ Manto Produções
          </div>
          <h1 className="mt-3 font-display text-3xl font-medium text-ink sm:text-4xl">
            Explore por categoria
          </h1>
          <p className="mx-auto mt-2 max-w-[46ch] text-[15.5px] text-muted">
            Cada seção reúne personagens de um mesmo tema — escolha uma para ver todas as
            opções.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-[1180px] px-6 pt-10">
        {isLoading && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[3/4] w-full" />
            ))}
          </div>
        )}

        {isError && (
          <div className="py-20 text-center text-muted">
            Não foi possível carregar as categorias agora. Tente novamente em instantes.
          </div>
        )}

        {data && data.categories.length > 0 && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {data.categories.map((category) => (
              <Link
                key={category.id}
                to={`/categoria/${category.slug}`}
                className="group relative aspect-[3/4] overflow-hidden rounded-lg bg-bg-alt shadow-sm transition-transform hover:-translate-y-1 hover:shadow-lg"
              >
                {category.cover_image_url && (
                  <img
                    src={assetUrl(category.cover_image_url)}
                    alt={category.name}
                    loading="lazy"
                    className="h-full w-full object-cover"
                    style={{ objectPosition: "center 15%" }}
                  />
                )}
                <div className="absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-ink/80 via-ink/15 to-transparent p-5">
                  <div className="font-display text-xl font-medium text-white">
                    {category.name}
                  </div>
                  <div className="text-[13px] font-semibold text-white/80">
                    {category.item_count} personagem{category.item_count === 1 ? "" : "s"}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {data && data.categories.length === 0 && (
          <div className="py-20 text-center text-muted">
            <div className="mb-3 text-4xl">🎭</div>
            <div>Nenhuma categoria disponível no momento.</div>
          </div>
        )}

        <p className="mt-9 text-center">
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-full border border-line px-6 py-3 text-sm font-semibold text-accent-dark hover:border-accent"
          >
            ← Ver catálogo completo
          </Link>
        </p>
      </main>

      <footer className="px-5 pb-12 pt-10 text-center text-[12.5px] text-muted">
        Manto Produções — personagens vivos para o seu evento
      </footer>
    </div>
  );
}
