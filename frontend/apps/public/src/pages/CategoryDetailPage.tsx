import { Link, useParams } from "react-router-dom";
import { Skeleton } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { useCategoryDetail } from "../lib/catalogo";
import { ProductCard } from "../components/ProductCard";

export function CategoryDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, isLoading, error } = useCategoryDetail(slug);

  const notFound = error instanceof ApiRequestError && error.status === 404;

  if (notFound) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
        <div className="mb-3 text-4xl">🎭</div>
        <p className="mb-6 text-muted">Esta categoria não foi encontrada.</p>
        <Link
          to="/categorias"
          className="inline-flex items-center gap-2 rounded-full border border-line px-6 py-3 text-sm font-semibold text-accent-dark hover:border-accent"
        >
          ← Todas as categorias
        </Link>
      </div>
    );
  }

  return (
    <div className="pb-24">
      <div className="border-b border-line px-6 py-5">
        <div className="mx-auto max-w-[1180px]">
          <Link to="/categorias" className="text-[13.5px] font-semibold text-muted hover:text-accent">
            ← Todas as categorias
          </Link>
        </div>
      </div>

      {data && (
        <header className="px-6 py-9 text-center">
          <div className="mx-auto max-w-[1180px]">
            <div className="text-xs font-bold uppercase tracking-[0.16em] text-gold">
              ✦ Manto Produções
            </div>
            <h1 className="mt-2 font-display text-3xl font-medium text-ink sm:text-4xl">
              {data.category.name}
            </h1>
            <p className="mt-1.5 text-sm text-muted">
              {data.items.length} personagem{data.items.length === 1 ? "" : "s"} nesta seção
            </p>
          </div>
        </header>
      )}

      <main className="mx-auto max-w-[1180px] px-6">
        {isLoading && (
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="aspect-square w-full" />
            ))}
          </div>
        )}

        {data && (
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3">
            {data.items.map((item) => (
              <ProductCard key={item.id} item={item} large />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
