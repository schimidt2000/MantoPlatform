import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Skeleton } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { useProductDetail } from "../lib/catalogo";
import { ProductGallery } from "../components/ProductGallery";
import { WishlistButton } from "../components/WishlistButton";
import { ProductCard } from "../components/ProductCard";
import { CharacterGrid } from "../components/CharacterGrid";

export function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams] = useSearchParams();
  const highlightedPersonagem = searchParams.get("personagem");
  const { data, isLoading, error } = useProductDetail(slug);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (data) {
      document.title = `${data.name} — Catálogo Manto Produções`;
    }
    return () => {
      document.title = "Manto Produções";
    };
  }, [data]);

  useEffect(() => {
    if (!data || !highlightedPersonagem) return;
    const el = document.getElementById(`personagem-${highlightedPersonagem}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [data, highlightedPersonagem]);

  const notFound = error instanceof ApiRequestError && error.status === 404;

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      // clipboard indisponível — ignora, o link continua visível na barra do navegador
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (notFound) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
        <div className="mb-3 text-4xl">🎭</div>
        <p className="mb-6 text-muted">Este personagem não foi encontrado.</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-full border border-line px-6 py-3 text-sm font-semibold text-accent-dark hover:border-accent"
        >
          ← Voltar ao catálogo
        </Link>
      </div>
    );
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

      <main className="mx-auto max-w-[1180px] px-6 py-10">
        {isLoading && (
          <div className="grid gap-10 md:grid-cols-[1.1fr_1fr]">
            {/* Mesma altura mínima do palco da galeria — o esqueleto não pode ter um tamanho
                que a foto real nunca vai ter, senão a página salta ao carregar. */}
            <Skeleton className="h-[380px] w-full" />
            <div className="space-y-3">
              <Skeleton className="h-10 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </div>
        )}

        {data && (
          <>
            <div className="grid items-start gap-7 md:grid-cols-[1.1fr_1fr] md:gap-12">
              <ProductGallery
                images={data.images}
                name={data.name}
                videoUrl={data.video_url}
                videoKind={data.video_kind}
              />

              {/* `min-w-0` nas duas colunas: sem isso o conteúdo intrínseco (foto grande de um
                  lado, palavra longa do outro) rouba a largura da outra e o layout deixa de
                  seguir a proporção 1.1fr/1fr. */}
              <div className="min-w-0">
                <div className="text-xs font-bold uppercase tracking-[0.16em] text-gold">
                  ✦ Manto Produções
                </div>
                <h1 className="mt-3 text-balance font-display text-3xl font-medium text-ink sm:text-4xl">
                  {data.name}
                </h1>
                <div className="mb-5 mt-3 flex flex-wrap gap-1.5">
                  {data.categories.map((category) => (
                    <span
                      key={category.slug}
                      className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent-dark"
                    >
                      {category.name}
                    </span>
                  ))}
                </div>
                {/* Selo do tema-mãe (feature 209): esta página é a "página única" de um
                    personagem — o caminho de volta ao tema fica sempre visível. */}
                {data.parte_de_tema && (
                  <Link
                    to={`/${data.parte_de_tema.tema_slug}?personagem=${data.parte_de_tema.character_slug}`}
                    className="mb-5 -mt-2 inline-flex items-center gap-1.5 rounded-full border border-gold bg-gold/10 px-3 py-1 text-xs font-semibold text-accent-dark hover:bg-gold/20"
                  >
                    ✦ Parte do tema {data.parte_de_tema.tema_name} — ver elenco completo
                  </Link>
                )}
                {/* `strong`/`em`/`i` estilizados junto com `b`: o editor rich-text do admin
                    emite `<b>`/`<i>` na maioria dos browsers, mas alguns emitem `<strong>`/`<em>`. */}
                {data.description_html && (
                  <div
                    className="text-[15.5px] text-ink [&_b]:font-display [&_b]:text-[17px] [&_b]:font-semibold [&_strong]:font-display [&_strong]:text-[17px] [&_strong]:font-semibold [&_i]:italic [&_em]:italic [&_p]:mb-3 [&_div]:mb-3"
                    dangerouslySetInnerHTML={{ __html: data.description_html }}
                  />
                )}

                <div className="mt-7 flex flex-wrap gap-2.5">
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5"
                  >
                    {copied ? "✅ Copiado!" : "🔗 Copiar link"}
                  </button>
                  <WishlistButton
                    slug={data.slug}
                    name={data.name}
                    cover={data.images[0]?.url ?? null}
                  />
                  {data.categories[0] && (
                    <Link
                      to={`/categoria/${data.categories[0].slug}`}
                      className="inline-flex items-center gap-2 rounded-full border border-line px-6 py-3 text-sm font-semibold text-accent-dark hover:border-accent"
                    >
                      Ver mais em {data.categories[0].name}
                    </Link>
                  )}
                </div>
              </div>
            </div>

            <CharacterGrid
              characters={data.characters}
              temaSlug={data.slug}
              highlightedSlug={highlightedPersonagem}
            />

            {data.related.length > 0 && (
              <div className="mt-16 border-t border-line pt-10">
                <h2 className="mb-5 text-balance font-display text-2xl font-medium text-ink sm:text-3xl">
                  Você também pode gostar
                </h2>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                  {data.related.map((item) => (
                    <ProductCard key={item.id} item={item} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
