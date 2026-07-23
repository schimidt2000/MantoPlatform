import { Outlet, NavLink } from "react-router-dom";
import { CalendarDays, Image, MailQuestion } from "lucide-react";
import { Button } from "@manto/ui";
import { useCurrentTalent, usePortalLogout } from "../lib/portalAuth";

const NAV_ITEMS = [
  { to: "/agenda", label: "Agenda", icon: CalendarDays },
  { to: "/convites", label: "Convites", icon: MailQuestion },
  { to: "/fotos-documentos", label: "Fotos", icon: Image },
];

/** Shell mobile-first do Portal do Artista: header + conteúdo + navegação inferior fixa. */
export function PortalShell() {
  const { data: talent } = useCurrentTalent();
  const logout = usePortalLogout();

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <header className="flex items-center justify-between border-b border-line bg-panel px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">
            {talent?.artistic_name || talent?.full_name}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          loading={logout.isPending}
          onClick={() => logout.mutate()}
        >
          Sair
        </Button>
      </header>

      <main className="flex-1 pb-20">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-10 flex border-t border-line bg-panel">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-1 py-2.5 text-xs font-medium ${
                isActive ? "text-accent" : "text-muted"
              }`
            }
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
