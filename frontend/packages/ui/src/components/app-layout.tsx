import {
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { cn } from "../lib/cn";

/** Item de navegação do shell — `active` é calculado pelo app (o pacote não conhece o router). */
export interface NavItemData {
  key: string;
  label: string;
  href: string;
  icon?: ReactNode;
  active?: boolean;
  /** Abre em nova aba (ex.: catálogo público). */
  external?: boolean;
  /** Dica extra exibida via `title`. */
  hint?: string;
}

/** Grupo setorial de itens (Casting, Produção, Comercial…). Sem `label` = grupo do topo. */
export interface NavSectionData {
  label?: string;
  items: NavItemData[];
}

interface RenderLinkArgs {
  item: NavItemData;
  className: string;
  children: ReactNode;
  /** Deve ser chamado ao navegar — fecha o drawer no mobile. */
  onNavigate: () => void;
}

export interface AppLayoutProps {
  /** Bloco de marca no topo da sidebar (logo/nome). */
  brand: ReactNode;
  sections: NavSectionData[];
  /** Rodapé da sidebar (usuário, "Ver como", sair). */
  footer?: ReactNode;
  /**
   * Render prop para itens internos — o app injeta seu componente de rota
   * (ex.: `NavLink` do react-router). Itens `external` são renderizados pelo
   * próprio layout como `<a target="_blank">`.
   */
  renderLink: (args: RenderLinkArgs) => ReactNode;
  /** Título mostrado na barra superior do mobile. */
  mobileTitle?: string;
  children: ReactNode;
}

const NAV_ITEM_CLASS =
  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors";
// Os brancos daqui são LEGÍTIMOS nos dois temas e não devem virar `on-color`: a sidebar é
// escura no claro (#1f1a30) e no escuro (#2a2438), então o branco dá 14.92:1 e 13.4:1. Trocar
// por um token que inverte deixaria a coluna com texto preto sobre roxo escuro.
const NAV_ITEM_IDLE = "text-white/65 hover:bg-white/5 hover:text-white";
const NAV_ITEM_ACTIVE = "bg-white/10 text-white";

function navItemClass(active: boolean | undefined): string {
  return cn(NAV_ITEM_CLASS, active ? NAV_ITEM_ACTIVE : NAV_ITEM_IDLE);
}

function NavItemContent({ item }: { item: NavItemData }) {
  return (
    <>
      {item.icon && (
        <span aria-hidden className="flex h-4 w-4 shrink-0 items-center justify-center [&>svg]:h-4 [&>svg]:w-4">
          {item.icon}
        </span>
      )}
      <span className="truncate">{item.label}</span>
    </>
  );
}

function SidebarNav({
  sections,
  renderLink,
  onNavigate,
}: Pick<AppLayoutProps, "sections" | "renderLink"> & { onNavigate: () => void }) {
  return (
    <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
      {sections.map((section, index) => (
        <div key={section.label ?? `top-${index}`} className="space-y-0.5">
          {section.label && (
            // white/35 sobre a sidebar #1f1a30 dava 3.19:1 a 11px — reprovava AA. white/60
            // dá 6.75:1; o `uppercase`/`tracking-wider` já entrega a discrição que a
            // opacidade baixa buscava, e a hierarquia se mantém pelo branco puro dos itens.
            <div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-white/60">
              {section.label}
            </div>
          )}
          {section.items.map((item) =>
            item.external ? (
              <a
                key={item.key}
                href={item.href}
                target="_blank"
                rel="noopener"
                title={item.hint}
                className={navItemClass(item.active)}
              >
                <NavItemContent item={item} />
              </a>
            ) : (
              <span key={item.key} className="block" title={item.hint}>
                {renderLink({
                  item,
                  className: navItemClass(item.active),
                  children: <NavItemContent item={item} />,
                  onNavigate,
                })}
              </span>
            ),
          )}
        </div>
      ))}
    </nav>
  );
}

/**
 * Shell institucional da Plataforma Manto (feature 173): sidebar fixa roxa escura no
 * desktop, drawer retrátil no mobile, navegação agrupada por setor e rodapé com o
 * usuário/"Ver como". Transições via framer-motion respeitando `prefers-reduced-motion`.
 */
function AppLayout({
  brand,
  sections,
  footer,
  renderLink,
  mobileTitle = "Manto",
  children,
}: AppLayoutProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const reduceMotion = useReducedMotion();
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  // Fecha o drawer com Esc e quando o viewport cresce para desktop (sem overlay órfão).
  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDrawer();
    };
    const desktop = window.matchMedia("(min-width: 1024px)");
    const onChange = () => {
      if (desktop.matches) closeDrawer();
    };
    window.addEventListener("keydown", onKeyDown);
    desktop.addEventListener("change", onChange);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      desktop.removeEventListener("change", onChange);
    };
  }, [drawerOpen, closeDrawer]);

  const sidebarInner = (
    <div className="flex h-full flex-col">
      <div className="border-b border-white/10 px-5 py-4">{brand}</div>
      <SidebarNav sections={sections} renderLink={renderLink} onNavigate={closeDrawer} />
      {footer && <div className="border-t border-white/10 px-3 py-3">{footer}</div>}
    </div>
  );

  return (
    <div className="min-h-screen bg-bg lg:pl-64">
      {/* Sidebar fixa — desktop */}
      {/* A costura da direita só aparece no tema escuro: lá `sidebar-line` é um roxo mais
          claro que separa a coluna do fundo da página (1.27:1 sozinho é sutil demais); no tema
          claro o token vale o próprio `sidebar-bg`, então a borda some — a sidebar escura já
          se destaca sobre a página clara sem ajuda nenhuma. */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-sidebar-line bg-sidebar-bg lg:block">
        {sidebarInner}
      </aside>

      {/* Barra superior — mobile */}
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-panel px-4 lg:hidden">
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-label="Abrir menu"
          title="Abrir menu"
          className="flex h-11 w-11 items-center justify-center rounded-md text-ink hover:bg-surface-2"
        >
          <Menu className="h-5 w-5" aria-hidden />
        </button>
        <span className="text-base font-semibold text-ink">{mobileTitle}</span>
      </header>

      {/* Drawer — mobile */}
      <AnimatePresence>
        {drawerOpen && (
          <>
            <motion.div
              key="overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: reduceMotion ? 0 : 0.2 }}
              onClick={closeDrawer}
              className="fixed inset-0 z-40 bg-black/50 lg:hidden"
              aria-hidden
            />
            <motion.aside
              key="drawer"
              initial={{ x: reduceMotion ? 0 : "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: reduceMotion ? 0 : "-100%", opacity: reduceMotion ? 0 : 1 }}
              transition={{ duration: reduceMotion ? 0 : 0.25, ease: "easeOut" }}
              className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-sidebar-bg lg:hidden"
            >
              <button
                type="button"
                onClick={closeDrawer}
                aria-label="Fechar menu"
                title="Fechar menu"
                className="absolute right-2 top-3 flex h-11 w-11 items-center justify-center rounded-md text-white/70 hover:bg-white/10 hover:text-white"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
              {sidebarInner}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <main className="min-h-screen">{children}</main>
    </div>
  );
}

export { AppLayout };
