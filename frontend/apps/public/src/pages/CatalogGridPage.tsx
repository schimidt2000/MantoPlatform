import { useMemo } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { Skeleton, useRestaurarRolagem } from "@manto/ui";
import { useChegouPeloHistorico } from "../lib/navegacao";
import { useCatalogList } from "../lib/catalogo";
import { ProductCard } from "../components/ProductCard";

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

export function CatalogGridPage() {
  const { data, isLoading, isError } = useCatalogList();
  // Busca e categoria moram no endereço (feature 320): voltar de um tema, recarregar ou abrir o
  // link copiado reproduz a mesma lista. `replace` para não criar um "voltar" por letra digitada.
  const [params, setParams] = useSearchParams();
  const search = params.get("q") ?? "";
  const activeCategory = params.get("categoria") ?? "";
  const location = useLocation();
  const voltou = useChegouPeloHistorico();
  useRestaurarRolagem(location.key, { restaurar: voltou, pronto: Boolean(data) });

  function setFiltro(chave: "q" | "categoria", valor: string) {
    setParams(
      (atual) => {
        const proximo = new URLSearchParams(atual);
        if (valor) proximo.set(chave, valor);
        else proximo.delete(chave);
        return proximo;
      },
      { replace: true, state: location.state },
    );
  }
  const setSearch = (valor: string) => setFiltro("q", valor);
  const setActiveCategory = (valor: string) => setFiltro("categoria", valor);

  const filtered = useMemo(() => {
    if (!data) return [];
    const term = normalize(search.trim());
    return data.items.filter((item) => {
      // Tags entram na busca (feature 209): "alice" acha o Coelho Branco pela tag, sem
      // poluir a grade com personagens sem página própria.
      const searchText = normalize([item.name, ...item.categories, ...item.tags].join(" "));
      const matchesSearch = !term || searchText.includes(term);
      const matchesCategory = !activeCategory || item.categories.includes(activeCategory);
      return matchesSearch && matchesCategory;
    });
  }, [data, search, activeCategory]);

  return (
    <div className="pb-24">
      <header className="border-b border-line bg-gradient-to-b from-bg-alt to-bg px-6 py-16 text-center">
        <div className="mx-auto max-w-[1180px]">
          <div className="text-xs font-bold uppercase tracking-[0.16em] text-gold">
            ✦ Manto Produções
          </div>
          <h1 className="mt-3 font-display text-4xl font-medium text-ink sm:text-5xl">
            Nosso catálogo de personagens
          </h1>
          <p className="mx-auto mt-3 max-w-[46ch] text-muted">
            Shows, personagens e temas prontos para transformar o seu evento num momento
            mágico. Busque por nome, tema ou clima — ou explore por seção.
          </p>
          <div className="mx-auto mt-8 max-w-[480px]">
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nome, tema, estilo…"
              autoComplete="off"
              className="w-full rounded-full border border-line bg-panel px-5 py-3.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <p className="mt-4">
            <Link
              to="/categorias"
              className="inline-flex items-center gap-2 rounded-full border border-line px-6 py-3 text-sm font-semibold text-accent-dark hover:border-accent"
            >
              📂 Ver por categoria
            </Link>
          </p>
        </div>
      </header>

      <div className="mx-auto max-w-[1180px] px-6">
        {data && (
          <div className="flex gap-2 overflow-x-auto py-5">
            <button
              type="button"
              onClick={() => setActiveCategory("")}
              className={`flex-none rounded-full border px-[18px] py-2 text-[13.5px] font-semibold ${
                activeCategory === ""
                  ? "border-accent bg-accent text-white"
                  : "border-line bg-panel text-ink"
              }`}
            >
              Todos ({data.total})
            </button>
            {data.categories.map((category) => (
              <button
                key={category.id}
                type="button"
                onClick={() => setActiveCategory(category.name)}
                className={`flex-none whitespace-nowrap rounded-full border px-[18px] py-2 text-[13.5px] font-semibold ${
                  activeCategory === category.name
                    ? "border-accent bg-accent text-white"
                    : "border-line bg-panel text-ink"
                }`}
              >
                {category.name} ({category.item_count})
              </button>
            ))}
          </div>
        )}

        <main className="pt-2">
          {isLoading && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="aspect-[4/5] w-full" />
              ))}
            </div>
          )}

          {isError && (
            <div className="py-20 text-center text-muted">
              Não foi possível carregar o catálogo agora. Tente novamente em instantes.
            </div>
          )}

          {data && (
            <>
              <div className="mb-5 text-[13px] text-muted">
                {filtered.length === 1
                  ? "1 personagem encontrado"
                  : `${filtered.length} personagens encontrados`}
              </div>
              {filtered.length > 0 ? (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                  {filtered.map((item) => (
                    <ProductCard key={item.id} item={item} deLista />
                  ))}
                </div>
              ) : (
                <div className="py-20 text-center text-muted">
                  <div className="mb-3 text-4xl">🔎</div>
                  <div>Nenhum personagem encontrado. Tente outro termo ou seção.</div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      <footer className="px-5 pb-12 pt-8 text-center text-[12.5px] text-muted">
        Manto Produções — personagens vivos para o seu evento
      </footer>
    </div>
  );
}
