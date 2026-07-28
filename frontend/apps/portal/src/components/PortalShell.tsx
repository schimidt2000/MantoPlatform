import { Outlet, NavLink, Link } from "react-router-dom";
import { CalendarDays, History, MailQuestion, User } from "lucide-react";
import { assetUrl } from "@manto/api-client";
import { Button } from "@manto/ui";
import { useCurrentTalent, usePortalLogout } from "../lib/portalAuth";
import { useAgenda } from "../lib/portalAgenda";
import { usePendingRatings } from "../lib/portalRatings";

const NAV_ITEMS = [
  { to: "/agenda", label: "Agenda", icon: CalendarDays },
  { to: "/convites", label: "Convites", icon: MailQuestion },
  { to: "/historico", label: "Histórico", icon: History },
  { to: "/perfil", label: "Perfil", icon: User },
];

/** Contador de pendências sobre o ícone da aba (convites a responder, eventos a avaliar). */
function NavBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span
      className="absolute -right-2 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red px-1 text-xs font-bold leading-none text-white"
      aria-label={`${count} ${count === 1 ? "pendência" : "pendências"}`}
    >
      {count > 9 ? "9+" : count}
    </span>
  );
}

/** Shell mobile-first do Portal do Artista: header + conteúdo + navegação inferior fixa. */
export function PortalShell() {
  const { data: talent } = useCurrentTalent();
  const logout = usePortalLogout();
  const { data: agenda } = useAgenda();
  const { data: ratings } = usePendingRatings();

  const pendingByRoute: Record<string, number> = {
    "/convites": agenda?.pending_invites.length ?? 0,
    "/historico": ratings?.rateable_event_ids.length ?? 0,
  };

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <header className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line bg-panel px-4 py-3">
        <Link to="/perfil" className="flex min-h-[44px] min-w-0 flex-1 items-center gap-3">
          {talent?.photo_face_url ? (
            <img
              src={assetUrl(talent.photo_face_url)}
              alt=""
              className="h-9 w-9 shrink-0 rounded-full object-cover"
            />
          ) : (
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent">
              {(talent?.artistic_name || talent?.full_name || "?").charAt(0).toUpperCase()}
            </span>
          )}
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-ink">
              {talent?.artistic_name || talent?.full_name}
            </span>
            <span className="block text-xs text-muted">Ver meu perfil</span>
          </span>
        </Link>
        <Button
          variant="ghost"
          size="sm"
          className="min-h-[44px] shrink-0"
          loading={logout.isPending}
          onClick={() => logout.mutate()}
        >
          Sair
        </Button>
      </header>

      <main className="flex-1 pb-24">
        <Outlet />
      </main>

      <nav
        aria-label="Navegação principal"
        className="fixed inset-x-0 bottom-0 z-10 flex border-t border-line bg-panel pb-[env(safe-area-inset-bottom)]"
      >
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex min-h-[56px] flex-1 flex-col items-center justify-center gap-1 py-2 text-xs font-medium ${
                isActive ? "text-accent" : "text-muted"
              }`
            }
          >
            <span className="relative">
              <Icon className="h-5 w-5" aria-hidden="true" />
              <NavBadge count={pendingByRoute[to] ?? 0} />
            </span>
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
