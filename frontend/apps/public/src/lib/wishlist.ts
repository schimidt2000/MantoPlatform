/**
 * Lista de desejos do catálogo público — porta de `app/static/js/catalogo-wishlist.js`
 * (feature 140) para TypeScript, mesma chave/formato de `localStorage` (research.md §5).
 *
 * 100% client-side — não existe conta de cliente na parte pública do catálogo, então a lista
 * fica só no navegador da pessoa (sobrevive a fechar a aba, não sincroniza entre aparelhos).
 */

const STORAGE_KEY = "manto_catalogo_wishlist";

export interface WishlistItem {
  slug: string;
  name: string;
  cover: string;
  /** "tema" (default implícito para itens salvos antes da feature 185) | "personagem". */
  kind?: "tema" | "personagem";
  /** Slug do Tema pai — só preenchido quando `kind === "personagem"` (feature 185). */
  parentSlug?: string;
}

/**
 * `BASE_URL` reflete o `base` do Vite ("/" em dev, "/catalogo/" em produção — feature 186, US6)
 * — path relativo bruto (fora do React Router) precisa desse prefixo manualmente.
 */
function itemUrl(item: WishlistItem): string {
  const base = import.meta.env.BASE_URL;
  if (item.kind === "personagem" && item.parentSlug) {
    return `${base}${item.parentSlug}?personagem=${item.slug}`;
  }
  return `${base}${item.slug}`;
}

function getAll(): WishlistItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function saveAll(list: WishlistItem[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {
    // localStorage indisponível (modo privado/cota) — degrada sem quebrar a página
  }
}

function has(slug: string): boolean {
  return getAll().some((item) => item.slug === slug);
}

function add(item: WishlistItem): WishlistItem[] {
  const list = getAll();
  if (!item.slug || list.some((i) => i.slug === item.slug)) {
    return list;
  }
  const next = [...list, item];
  saveAll(next);
  return next;
}

function remove(slug: string): WishlistItem[] {
  const next = getAll().filter((item) => item.slug !== slug);
  saveAll(next);
  return next;
}

function toggle(item: WishlistItem): WishlistItem[] {
  return has(item.slug) ? remove(item.slug) : add(item);
}

function count(): number {
  return getAll().length;
}

function buildMessage(): string {
  const list = getAll();
  if (list.length === 0) return "";
  const lines = ["Olá! Vi esses personagens no catálogo e gostaria de saber mais:", ""];
  const baseUrl = window.location.origin;
  for (const item of list) {
    lines.push(`• ${item.name} — ${baseUrl}${itemUrl(item)}`);
  }
  return lines.join("\n");
}

function whatsappUrl(phoneNumber: string): string | null {
  const message = buildMessage();
  if (!message) return null;
  return `https://api.whatsapp.com/send?phone=${phoneNumber}&text=${encodeURIComponent(message)}`;
}

export const wishlist = {
  getAll,
  has,
  add,
  remove,
  toggle,
  count,
  buildMessage,
  whatsappUrl,
};
