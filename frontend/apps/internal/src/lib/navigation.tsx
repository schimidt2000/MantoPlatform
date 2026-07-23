import type { ReactNode } from "react";
import {
  BarChart3,
  BookOpen,
  Calculator,
  CalendarDays,
  Clapperboard,
  ClipboardCheck,
  DollarSign,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  History,
  Home,
  LineChart,
  ListChecks,
  Package,
  PenSquare,
  Plus,
  Receipt,
  RefreshCw,
  Repeat,
  Settings,
  Shirt,
  SlidersHorizontal,
  Star,
  Users,
  Wallet,
  WalletCards,
} from "lucide-react";
import type { NavSectionData } from "@manto/ui";
import type { AuthUser } from "./types";

/**
 * Config declarativa da navegação do shell (feature 173), portada de
 * `app/templates/base.html` — mesma ordem, mesmos rótulos e mesmas regras de
 * visibilidade por papel EFETIVO. Itens ainda só em Jinja (Gastos, Orçamento,
 * Formulários, Avaliação de Casting) apontam para a rota clássica via
 * `external: true` — mesmo padrão do link "Catálogo" — até ganharem tela em React.
 */

interface NavItemConfig {
  key: string;
  label: string;
  href: string;
  icon: ReactNode;
  external?: boolean;
  hint?: string;
  isActive: (pathname: string) => boolean;
  isVisible: (user: AuthUser) => boolean;
}

interface NavSectionConfig {
  label?: string;
  items: NavItemConfig[];
}

/** Papéis efetivos: com "Ver como" ativo, o usuário conta só com o papel simulado. */
function effectiveRoles(user: AuthUser): string[] {
  return user.impersonating ? [user.impersonating] : user.roles;
}

function hasRole(user: AuthUser, ...names: string[]): boolean {
  const roles = effectiveRoles(user);
  return names.some((name) => roles.includes(name));
}

/** Perfil restrito (feature 078): só REVENDEDOR_EDUCAMANTO — vê apenas Agenda + EducaManto. */
function isRevendedorOnly(user: AuthUser): boolean {
  const roles = effectiveRoles(user);
  return roles.includes("REVENDEDOR_EDUCAMANTO") && roles.length === 1;
}

const everyone = () => true;
const notRevendedor = (user: AuthUser) => !isRevendedorOnly(user);

const SECTIONS: NavSectionConfig[] = [
  {
    items: [
      {
        key: "home",
        label: "Home",
        href: "/",
        icon: <Home />,
        isActive: (path) => path === "/",
        isVisible: notRevendedor,
      },
      {
        key: "agenda",
        label: "Agenda",
        href: "/agenda",
        icon: <CalendarDays />,
        isActive: (path) =>
          path === "/agenda" || (path.startsWith("/events/") && path !== "/events/new"),
        isVisible: everyone,
      },
      {
        key: "gastos-extras",
        label: "Gastos Extras",
        href: "/gastos/",
        icon: <Receipt />,
        external: true,
        hint: "Tela clássica — abre em outra aba",
        isActive: () => false,
        isVisible: notRevendedor,
      },
    ],
  },
  {
    label: "Casting",
    items: [
      {
        key: "talents",
        label: "Banco de Talentos",
        href: "/talents",
        icon: <Users />,
        isActive: (path) => path.startsWith("/talents"),
        isVisible: notRevendedor,
      },
      {
        key: "avaliacao-casting",
        label: "Avaliação de Casting",
        href: "/talents/avaliacoes",
        icon: <ClipboardCheck />,
        external: true,
        hint: "Tela clássica — abre em outra aba",
        isActive: () => false,
        isVisible: notRevendedor,
      },
    ],
  },
  {
    label: "Produção",
    items: [
      {
        key: "revisao",
        label: "Revisão",
        href: "/revisao",
        icon: <Clapperboard />,
        isActive: (path) => path.startsWith("/revisao"),
        isVisible: notRevendedor,
      },
      {
        key: "figurinos",
        label: "Figurinos",
        href: "/figurinos",
        icon: <Shirt />,
        isActive: (path) => path.startsWith("/figurinos"),
        isVisible: notRevendedor,
      },
    ],
  },
  {
    label: "Comercial",
    items: [
      {
        key: "novo-evento",
        label: "Novo Evento",
        href: "/events/new",
        icon: <Plus />,
        isActive: (path) => path === "/events/new",
        isVisible: (user) => notRevendedor(user) && hasRole(user, "COMERCIAL", "SUPERADMIN"),
      },
      {
        key: "vendas",
        label: "Pipeline de Vendas",
        href: "/vendas",
        icon: <BarChart3 />,
        isActive: (path) => path.startsWith("/vendas"),
        isVisible: (user) =>
          notRevendedor(user) &&
          (hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN") ||
            user.is_educamanto_responsavel),
      },
      {
        key: "clientes",
        label: "Clientes",
        href: "/clientes",
        icon: <Users />,
        isActive: (path) => path.startsWith("/clientes") && !path.includes("avaliacoes"),
        isVisible: (user) =>
          notRevendedor(user) && hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN"),
      },
      {
        key: "avaliacoes-clientes",
        label: "Avaliações",
        href: "/clientes/avaliacoes",
        icon: <Star />,
        isActive: (path) => path === "/clientes/avaliacoes",
        isVisible: (user) =>
          notRevendedor(user) && hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN"),
      },
      {
        key: "catalogo-publico",
        label: "Catálogo",
        href: "/catalogo/",
        icon: <BookOpen />,
        external: true,
        hint: "Abre o catálogo público em outra aba",
        isActive: () => false,
        isVisible: (user) =>
          notRevendedor(user) && hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN"),
      },
      {
        key: "admin-catalogo",
        label: "Gerenciar catálogo",
        href: "/admin/catalogo",
        icon: <PenSquare />,
        hint: "Criar e editar produtos do catálogo",
        isActive: (path) => path.startsWith("/admin/catalogo"),
        isVisible: (user) => notRevendedor(user) && hasRole(user, "SUPERADMIN"),
      },
      {
        key: "comissoes",
        label: "Comissões",
        href: "/financeiro/comissoes",
        icon: <DollarSign />,
        isActive: (path) => path === "/financeiro/comissoes",
        isVisible: (user) =>
          notRevendedor(user) &&
          (hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN") ||
            user.is_educamanto_responsavel),
      },
      {
        key: "formularios",
        label: "Formulários",
        href: "/formularios/",
        icon: <FileText />,
        external: true,
        hint: "Tela clássica — abre em outra aba",
        isActive: () => false,
        isVisible: (user) =>
          notRevendedor(user) && hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN"),
      },
    ],
  },
  {
    label: "Financeiro",
    items: [
      {
        key: "financeiro",
        label: "Painel Financeiro",
        href: "/financeiro",
        icon: <Wallet />,
        isActive: (path) => path === "/financeiro",
        isVisible: (user) => hasRole(user, "FINANCEIRO", "SUPERADMIN"),
      },
      {
        key: "pagamentos",
        label: "Pagamentos",
        href: "/financeiro/pagamentos",
        icon: <WalletCards />,
        isActive: (path) => path === "/financeiro/pagamentos",
        isVisible: (user) => hasRole(user, "FINANCEIRO", "SUPERADMIN"),
      },
      {
        key: "gastos-recorrentes",
        label: "Gastos Recorrentes",
        href: "/gastos/recorrentes",
        icon: <Repeat />,
        external: true,
        hint: "Tela clássica — abre em outra aba",
        isActive: () => false,
        isVisible: (user) => hasRole(user, "FINANCEIRO", "SUPERADMIN"),
      },
    ],
  },
  {
    label: "Ferramentas",
    items: [
      {
        key: "calc-orcamento",
        label: "Calc. Orçamento",
        href: "/orcamento/",
        icon: <Calculator />,
        external: true,
        hint: "Tela clássica — abre em outra aba",
        isActive: () => false,
        isVisible: (user) => hasRole(user, "COMERCIAL", "SUPERADMIN"),
      },
      {
        key: "config-precos",
        label: "Config. Preços",
        href: "/orcamento/settings",
        icon: <SlidersHorizontal />,
        external: true,
        hint: "Tela clássica — abre em outra aba",
        isActive: () => false,
        isVisible: (user) => hasRole(user, "SUPERADMIN"),
      },
      {
        key: "orcamentos",
        label: "Orçamentos",
        href: "/orcamento/historico",
        icon: <FileSpreadsheet />,
        external: true,
        hint: "Tela clássica — abre em outra aba",
        isActive: () => false,
        isVisible: (user) => hasRole(user, "COMERCIAL", "SUPERADMIN"),
      },
      {
        key: "educamanto",
        label: "EducaManto",
        href: "/educamanto",
        icon: <GraduationCap />,
        isActive: (path) => path === "/educamanto",
        isVisible: (user) =>
          hasRole(user, "COMERCIAL", "SUPERADMIN", "ENSAIO", "REVENDEDOR_EDUCAMANTO"),
      },
      {
        key: "educamanto-pacotes",
        label: "Pacotes EducaManto",
        href: "/educamanto/pacotes",
        icon: <Package />,
        isActive: (path) => path.startsWith("/educamanto/pacotes"),
        isVisible: (user) => hasRole(user, "COMERCIAL", "SUPERADMIN"),
      },
      {
        key: "educamanto-historico",
        label: "Histórico EducaManto",
        href: "/educamanto/historico",
        icon: <History />,
        isActive: (path) => path === "/educamanto/historico",
        isVisible: (user) =>
          hasRole(user, "COMERCIAL", "SUPERADMIN", "ENSAIO", "REVENDEDOR_EDUCAMANTO"),
      },
    ],
  },
  {
    label: "Sistema",
    items: [
      {
        key: "admin-usuarios",
        label: "Usuários",
        href: "/admin/usuarios",
        icon: <Users />,
        isActive: (path) => path.startsWith("/admin/usuarios"),
        isVisible: (user) => hasRole(user, "SUPERADMIN", "FINANCEIRO"),
      },
      {
        key: "admin-config",
        label: "Administração",
        href: "/admin/configuracoes",
        icon: <Settings />,
        isActive: (path) =>
          path.startsWith("/admin") &&
          !path.startsWith("/admin/usuarios") &&
          !path.startsWith("/admin/catalogo") &&
          !path.startsWith("/admin/desempenho") &&
          !path.startsWith("/admin/logs") &&
          !path.startsWith("/admin/sync"),
        isVisible: (user) => hasRole(user, "SUPERADMIN"),
      },
      {
        key: "admin-desempenho",
        label: "Desempenho",
        href: "/admin/desempenho",
        icon: <LineChart />,
        isActive: (path) => path.startsWith("/admin/desempenho"),
        isVisible: (user) => hasRole(user, "SUPERADMIN"),
      },
      {
        key: "admin-logs",
        label: "Logs",
        href: "/admin/logs",
        icon: <ListChecks />,
        isActive: (path) => path.startsWith("/admin/logs"),
        isVisible: (user) => hasRole(user, "SUPERADMIN"),
      },
      {
        key: "admin-sync",
        label: "Sincronização Agenda",
        href: "/admin/sync",
        icon: <RefreshCw />,
        isActive: (path) => path.startsWith("/admin/sync"),
        isVisible: (user) => hasRole(user, "SUPERADMIN"),
      },
    ],
  },
];

/** Monta as seções visíveis para o usuário na rota atual (grupos vazios somem). */
export function buildNavSections(user: AuthUser, pathname: string): NavSectionData[] {
  return SECTIONS.map((section) => ({
    label: section.label,
    items: section.items
      .filter((item) => item.isVisible(user))
      .map((item) => ({
        key: item.key,
        label: item.label,
        href: item.href,
        icon: item.icon,
        external: item.external,
        hint: item.hint,
        active: item.isActive(pathname),
      })),
  })).filter((section) => section.items.length > 0);
}
