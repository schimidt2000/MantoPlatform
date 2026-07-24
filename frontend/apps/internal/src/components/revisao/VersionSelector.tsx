import { Link } from "react-router-dom";
import { cn } from "@manto/ui";
import type { VersionInfo } from "../../lib/revisao";

export interface VersionSelectorProps {
  spaceId: number;
  assetId: number;
  /** Número da versão mais recente (a "atual" do material). */
  currentVersion: number;
  /** `null` quando exibindo a versão atual; caso contrário, a versão histórica em exibição. */
  viewingVersion: number | null;
  /** Versões antigas, da mais recente para a mais antiga (`asset.history`). */
  history: VersionInfo[];
}

function formatShortDate(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

/** Pills de versão no cabeçalho (feature 182, FR-012) — substitui a lista simples anterior. */
export function VersionSelector({ spaceId, assetId, currentVersion, viewingVersion, history }: VersionSelectorProps) {
  if (history.length === 0) return null;

  const base = `/revisao/${spaceId}/asset/${assetId}`;
  const isCurrent = viewingVersion === null;

  return (
    <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Versões do material">
      <Link
        to={base}
        role="tab"
        aria-selected={isCurrent}
        className={cn(
          "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
          isCurrent ? "border-accent bg-accent-soft text-accent-dark" : "border-line bg-panel text-muted hover:bg-surface-2",
        )}
      >
        v{currentVersion} (atual)
      </Link>
      {history
        .filter((v) => v.version_number !== currentVersion)
        .map((v) => {
          const active = viewingVersion === v.version_number;
          return (
            <Link
              key={v.version_number}
              to={`${base}?v=${v.version_number}`}
              role="tab"
              aria-selected={active}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                active ? "border-accent bg-accent-soft text-accent-dark" : "border-line bg-panel text-muted hover:bg-surface-2",
              )}
            >
              v{v.version_number}
              {v.created_at && ` (${formatShortDate(v.created_at)})`}
            </Link>
          );
        })}
    </div>
  );
}
