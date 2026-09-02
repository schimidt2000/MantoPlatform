import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { AppLayout, Skeleton, ThemeSwitch, cn } from "@manto/ui";
import { buildNavSections } from "../lib/navigation";
import {
  isRevendedorOnly,
  useCurrentUser,
  useImpersonate,
  useImpersonateReset,
  useLogout,
} from "../lib/useAuth";
import type { AuthUser } from "../lib/types";
import { NotificacoesBell } from "./notificacoes/NotificacoesBell";

/** Papéis simuláveis no "Ver como" — paridade com IMPERSONABLE_ROLES do backend. */
const IMPERSONABLE_ROLES = ["CASTING", "FIGURINO", "COMERCIAL", "FINANCEIRO", "ENSAIO"];

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-sidebar-accent/15 text-lg font-bold text-sidebar-accent">
        M
      </div>
      <div>
        <div className="text-base font-bold leading-tight text-white">Manto</div>
        {/* white/40 dava 3.79:1 a 11px sobre a sidebar #1f1a30; /60 sobe para 6.75:1. */}
        <div className="text-[11px] uppercase tracking-widest text-white/60">Plataforma</div>
      </div>
    </div>
  );
}

function RoleSwitcher({ user }: { user: AuthUser }) {
  const impersonate = useImpersonate();
  const reset = useImpersonateReset();
  const pending = impersonate.isPending || reset.isPending;

  if (!user.is_real_superadmin) return null;

  return (
    <div className="mb-2 border-b border-white/10 pb-2">
      <div className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/60">
        Ver como:
      </div>
      <div className="flex flex-wrap gap-1 px-2">
        {IMPERSONABLE_ROLES.map((role) => {
          const active = user.impersonating === role;
          return (
            <button
              key={role}
              type="button"
              disabled={pending || active}
              onClick={() => impersonate.mutate(role)}
              title={`Ver o sistema como ${role}`}
              className={cn(
                "rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors disabled:opacity-60",
                // Os brancos daqui ficam como estão: a sidebar é escura nos DOIS temas, então
                // `white/60` sobre o chip `white/10` dá 5.63:1 no claro e 5.09:1 no escuro.
                // Trocar por `on-color` (que inverte) deixaria o chip preto sobre roxo escuro.
                active
                  ? "bg-sidebar-accent text-sidebar-bg"
                  : "bg-white/10 text-white/60 hover:bg-white/20 hover:text-white",
              )}
            >
              {role}
            </button>
          );
        })}
        {user.impersonating && (
          <button
            type="button"
            disabled={pending}
            onClick={() => reset.mutate()}
            title="Voltar ao papel real de administrador"
            className="rounded-full border border-sidebar-accent/60 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-sidebar-accent transition-colors hover:bg-sidebar-accent/15 disabled:opacity-60"
          >
            {pending ? "..." : "Admin"}
          </button>
        )}
      </div>
    </div>
  );
}

function SidebarFooter({ user }: { user: AuthUser }) {
  const logout = useLogout();
  const navigate = useNavigate();

  return (
    <div className="space-y-2">
      <RoleSwitcher user={user} />
      <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sidebar-accent/20 text-sm font-semibold text-sidebar-accent">
          {user.name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-white">{user.name}</div>
          {/* white/45 = 4.41:1 a 11px (reprova AA); /70 sobe para 8.75:1. */}
          <div className="truncate text-[11px] text-white/70">
            {user.impersonating ? (
              <span className="font-semibold text-sidebar-accent">{user.impersonating}</span>
            ) : (
              user.roles.join(", ")
            )}
          </div>
        </div>
      </div>
      {/* Fica no rodapé (e não numa tela de preferências) porque o `AppLayout` renderiza este
          bloco DUAS vezes — sidebar do desktop e drawer do mobile —, então o switch aparece nos
          dois sem nenhuma duplicação de código. As instâncias compartilham estado via `useTheme`,
          que lê a classe do `<html>` em vez de guardar um `useState` por cópia. */}
      <ThemeSwitch />
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
        {/* Mesma costura do AppLayout — o esqueleto tem que nascer com a mesma silhueta. */}
        <div className="fixed inset-y-0 left-0 hidden w-64 border-r border-sidebar-line bg-sidebar-bg lg:block" />
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
      // Sino de notificações (feature 272). O revendedor EducaManto não recebe nenhum `kind` da
      // v1, então para ele o slot fica vazio.
      headerActions={isRevendedorOnly(user) ? undefined : <NotificacoesBell />}
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
