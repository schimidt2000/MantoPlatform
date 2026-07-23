import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { AppLayout, Skeleton } from "@manto/ui";
import { buildNavSections } from "../lib/navigation";
import { useCurrentUser, useLogout } from "../lib/useAuth";
import type { AuthUser } from "../lib/types";

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-sidebar-accent/15 text-lg font-bold text-sidebar-accent">
        M
      </div>
      <div>
        <div className="text-base font-bold leading-tight text-white">Manto</div>
        <div className="text-[11px] uppercase tracking-widest text-white/40">Plataforma</div>
      </div>
    </div>
  );
}

function SidebarFooter({ user }: { user: AuthUser }) {
  const logout = useLogout();
  const navigate = useNavigate();

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sidebar-accent/20 text-sm font-semibold text-sidebar-accent">
          {user.name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-white">{user.name}</div>
          <div className="truncate text-[11px] text-white/45">
            {user.impersonating ? (
              <span className="font-semibold text-sidebar-accent">{user.impersonating}</span>
            ) : (
              user.roles.join(", ")
            )}
          </div>
        </div>
      </div>
      <button
        type="button"
        onClick={() =>
          logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) })
        }
        disabled={logout.isPending}
        className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm font-medium text-white/55 transition-colors hover:bg-white/5 hover:text-white disabled:opacity-60"
      >
        <LogOut className="h-4 w-4" aria-hidden />
        {logout.isPending ? "Saindo..." : "Sair"}
      </button>
    </div>
  );
}

/**
 * Cola do shell com o app: injeta o `NavLink` do react-router no `AppLayout`,
 * monta a navegação RBAC a partir do usuário atual e renderiza as páginas via
 * `<Outlet/>` (layout route — feature 173).
 */
export function AppShell() {
  const { data: user, isLoading } = useCurrentUser();
  const { pathname } = useLocation();

  if (isLoading || !user) {
    // RequireAuth já cobre o redirect; aqui é só o esqueleto do shell (FR-012).
    return (
      <div className="min-h-screen bg-bg lg:pl-64">
        <div className="fixed inset-y-0 left-0 hidden w-64 bg-sidebar-bg lg:block" />
        <div className="space-y-4 p-6">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    );
  }

  return (
    <AppLayout
      brand={<Brand />}
      sections={buildNavSections(user, pathname)}
      footer={<SidebarFooter user={user} />}
      renderLink={({ item, className, children, onNavigate }) => (
        <NavLink to={item.href} className={className} onClick={onNavigate}>
          {children}
        </NavLink>
      )}
    >
      <Outlet />
    </AppLayout>
  );
}
