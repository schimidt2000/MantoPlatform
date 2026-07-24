import { Link } from "react-router-dom";
import { assetUrl } from "@manto/api-client";
import { Card, CardContent } from "@manto/ui";
import { KebabMenu } from "./KebabMenu";
import type { CatalogListItem } from "../lib/adminCatalogo";

interface CatalogCardGridProps {
  items: CatalogListItem[];
  selectedIds: Set<number>;
  onToggleSelect: (id: number) => void;
  onToggleActive: (item: CatalogListItem) => void;
  onDelete: (item: CatalogListItem) => void;
}

/**
 * Modo Cards do gerenciador (feature 186, US4) — mesma grade visual de sempre, mas com checkbox
 * de seleção e as ações "Inativar"/"Excluir" agora dentro de um `KebabMenu`, sem poluir o corpo
 * do card (FR-010). "Realocar/Mover" não aparece aqui: um Tema não tem pai a que se realocar
 * neste modelo de dados — mover é uma ação de Personagem, disponível no modo Árvore.
 */
export function CatalogCardGrid({
  items,
  selectedIds,
  onToggleSelect,
  onToggleActive,
  onDelete,
}: CatalogCardGridProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <Card key={item.id}>
          <CardContent className="flex gap-3 p-3">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 flex-none"
              checked={selectedIds.has(item.id)}
              onChange={() => onToggleSelect(item.id)}
              aria-label={`Selecionar ${item.name}`}
            />
            <div className="h-16 w-16 shrink-0 overflow-hidden rounded-md bg-surface-2">
              {item.cover_url && (
                <img
                  src={assetUrl(item.cover_url)}
                  alt={item.name}
                  className="h-full w-full object-cover"
                />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <Link
                  to={`/admin/catalogo/${item.id}/editar`}
                  className="font-medium text-ink hover:underline"
                >
                  {item.name}
                </Link>
                <KebabMenu
                  label={`Mais ações para ${item.name}`}
                  items={[
                    { label: "Editar", onClick: () => window.location.assign(`/admin/catalogo/${item.id}/editar`) },
                    { label: item.is_active ? "Inativar" : "Ativar", onClick: () => onToggleActive(item) },
                    { label: "Excluir", onClick: () => onDelete(item), destructive: true },
                  ]}
                />
              </div>
              {!item.is_active && (
                <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                  inativo
                </span>
              )}
              <div className="mt-1 text-xs text-muted">{item.category_names.join(", ")}</div>
              {item.characters.length > 0 && (
                <div className="mt-1 text-xs text-muted">
                  {item.characters.length} personagem{item.characters.length === 1 ? "" : "ns"}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
