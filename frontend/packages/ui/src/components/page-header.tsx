import { type ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "../lib/cn";

export interface BreadcrumbItem {
  label: string;
  /** Sem `href` = página atual (não vira link). */
  href?: string;
}

export interface PageHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  /** Trilha de navegação — o app injeta o link via `renderCrumb` (router-free). */
  breadcrumbs?: BreadcrumbItem[];
  /** Render prop para crumbs com `href` (ex.: `<Link>` do react-router). */
  renderCrumb?: (crumb: BreadcrumbItem, className: string) => ReactNode;
  /** Ações primárias — alinhadas à direita no desktop. */
  actions?: ReactNode;
  /** Filtros rápidos — linha abaixo do título. */
  filters?: ReactNode;
  className?: string;
}

const CRUMB_LINK_CLASS = "text-muted transition-colors hover:text-accent";

/**
 * Cabeçalho de página padrão do design system Manto (feature 173): título denso,
 * breadcrumbs opcionais, ações primárias à direita e área de filtros rápidos.
 */
function PageHeader({
  title,
  subtitle,
  breadcrumbs,
  renderCrumb,
  actions,
  filters,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn("mb-6 space-y-3", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Trilha de navegação" className="flex flex-wrap items-center gap-1 text-xs">
          {breadcrumbs.map((crumb, index) => (
            <span key={`${crumb.label}-${index}`} className="flex items-center gap-1">
              {index > 0 && <ChevronRight className="h-3 w-3 text-muted/60" aria-hidden />}
              {crumb.href && renderCrumb ? (
                renderCrumb(crumb, CRUMB_LINK_CLASS)
              ) : (
                <span className={cn(crumb.href ? CRUMB_LINK_CLASS : "font-medium text-ink")}>
                  {crumb.label}
                </span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold leading-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {filters && <div className="flex flex-wrap items-center gap-2">{filters}</div>}
    </header>
  );
}

export { PageHeader };
