import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { formatBRL } from "@manto/money";
import {
  Badge,
  Button,
  CheckboxList,
  FilterDropdown,
  PageHeader,
  Skeleton,
  Table,
  TableCell,
  TableRow,
} from "@manto/ui";
import { useAdminUsers, type AdminUser } from "../lib/adminUsers";
import { useCurrentUser } from "../lib/useAuth";

const INPUT = "h-9 rounded-md border border-line bg-panel px-3 text-sm text-ink";

type SortKey = "name" | "salary_desc" | "salary_asc" | "recent";

const SORT_LABELS: Record<SortKey, string> = {
  name: "Nome (A–Z)",
  salary_desc: "Maior salário",
  salary_asc: "Menor salário",
  recent: "Cadastrados por último",
};

/** Situação do vínculo — filtro combinável, cada chave é um predicado sobre o usuário. */
const SITUATION_OPTIONS = [
  { value: "ativo", label: "Ativo" },
  { value: "inativo", label: "Inativo" },
  { value: "acesso", label: "Com acesso" },
  { value: "so_pagamento", label: "Só pagamento" },
  { value: "comissao", label: "Recebe comissão" },
  { value: "sem_pix", label: "Sem chave PIX" },
];

const SITUATION_PREDICATES: Record<string, (u: AdminUser) => boolean> = {
  ativo: (u) => u.is_active,
  inativo: (u) => !u.is_active,
  acesso: (u) => u.has_access,
  so_pagamento: (u) => !u.has_access,
  comissao: (u) => u.receives_commission,
  sem_pix: (u) => !u.pix_key,
};

const PAYMENT_OPTIONS = [
  { value: "semanal", label: "Semanal" },
  { value: "quinzenal", label: "Quinzenal" },
  { value: "comissao", label: "Somente comissão" },
  { value: "sem_salario", label: "Sem salário vigente" },
];

const PAYMENT_LABELS: Record<string, string> = {
  semanal: "Semanal",
  quinzenal: "Quinzenal",
  comissao: "Comissão",
};

/** Segundas-feiras do mês corrente — mesma base que o backend usa para gerar salário semanal. */
function mondaysThisMonth(): number {
  const now = new Date();
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  let count = 0;
  for (let day = 1; day <= lastDay; day += 1) {
    if (new Date(now.getFullYear(), now.getMonth(), day).getDay() === 1) count += 1;
  }
  return count;
}

/**
 * Custo do usuário no mês corrente, na mesma cadência em que a planilha de pagamentos gera os
 * lançamentos: semanal cai em toda segunda-feira, quinzenal nos dias 5 e 20.
 */
function monthlyCost(user: AdminUser, mondays: number): number {
  if (!user.is_active || !user.salary) return 0;
  if (user.salary.payment_type === "semanal") return user.salary.amount * mondays;
  if (user.salary.payment_type === "quinzenal") return user.salary.amount * 2;
  return 0;
}

function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function SummaryTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md border border-line bg-panel px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</div>
      <div className="text-lg font-semibold tabular-nums text-ink">{value}</div>
      {hint && <div className="text-[11px] text-muted">{hint}</div>}
    </div>
  );
}

function UserRow({ user }: { user: AdminUser }) {
  return (
    <TableRow className={user.is_active ? undefined : "opacity-60"}>
      <TableCell>
        <Link
          to={`/admin/usuarios/${user.id}`}
          className="font-medium text-ink hover:text-accent hover:underline"
        >
          {user.name}
        </Link>
        <div className="text-xs text-muted">{user.email || "sem email"}</div>
      </TableCell>
      <TableCell className="hidden md:table-cell">
        {user.role_names.length === 0 ? (
          <span className="text-xs text-muted">—</span>
        ) : (
          <div className="flex flex-wrap gap-1">
            {user.role_names.map((role) => (
              <Badge key={role} tone="accent">
                {role}
              </Badge>
            ))}
          </div>
        )}
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {!user.is_active && <Badge tone="red">Inativo</Badge>}
          <Badge tone={user.has_access ? "blue" : "neutral"}>
            {user.has_access ? "Com acesso" : "Só pagamento"}
          </Badge>
        </div>
      </TableCell>
      <TableCell className="hidden lg:table-cell">
        {user.salary ? (
          <Badge tone={user.salary.payment_type === "comissao" ? "gold" : "neutral"}>
            {PAYMENT_LABELS[user.salary.payment_type] ?? user.salary.payment_type}
          </Badge>
        ) : (
          <span className="text-xs text-muted">—</span>
        )}
      </TableCell>
      <TableCell align="right" className="font-medium">
        {user.salary && user.salary.payment_type !== "comissao"
          ? `R$ ${formatBRL(user.salary.amount)}`
          : "—"}
      </TableCell>
      <TableCell className="hidden xl:table-cell">
        {user.pix_key ? (
          <div className="min-w-0">
            <div className="truncate text-xs text-ink" title={user.pix_key}>
              {user.pix_key}
            </div>
            {user.pix_key_type && (
              <div className="text-[11px] uppercase text-muted">{user.pix_key_type}</div>
            )}
          </div>
        ) : (
          <span className="text-xs text-muted">sem PIX</span>
        )}
      </TableCell>
    </TableRow>
  );
}

export function AdminUsersListPage() {
  const query = useAdminUsers();
  const { data: me } = useCurrentUser();

  const [search, setSearch] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [situations, setSituations] = useState<string[]>([]);
  const [payments, setPayments] = useState<string[]>([]);
  const [sort, setSort] = useState<SortKey>("name");

  const items = useMemo(() => query.data?.items ?? [], [query.data]);
  const mondays = useMemo(mondaysThisMonth, []);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    const filtered = items.filter((user) => {
      if (term && !`${user.name} ${user.email}`.toLowerCase().includes(term)) return false;
      if (roles.length > 0 && !user.role_names.some((r) => roles.includes(r))) return false;
      // Situações se somam como restrições (E), para "ativo + sem PIX" funcionar como se lê.
      if (situations.some((key) => !SITUATION_PREDICATES[key]?.(user))) return false;
      if (payments.length > 0) {
        const key = user.salary?.payment_type ?? "sem_salario";
        if (!payments.includes(key)) return false;
      }
      return true;
    });

    const byName = (a: AdminUser, b: AdminUser) => a.name.localeCompare(b.name, "pt-BR");
    const amount = (u: AdminUser) => u.salary?.amount ?? 0;
    return [...filtered].sort((a, b) => {
      if (sort === "salary_desc") return amount(b) - amount(a) || byName(a, b);
      if (sort === "salary_asc") return amount(a) - amount(b) || byName(a, b);
      if (sort === "recent") return b.id - a.id;
      return byName(a, b);
    });
  }, [items, search, roles, situations, payments, sort]);

  const totals = useMemo(() => {
    const active = visible.filter((u) => u.is_active);
    return {
      active: active.length,
      withAccess: visible.filter((u) => u.has_access).length,
      payroll: visible.reduce((sum, u) => sum + monthlyCost(u, mondays), 0),
    };
  }, [visible, mondays]);

  const activeFilters = roles.length + situations.length + payments.length + (search ? 1 : 0);
  const roleOptions = (query.data?.all_roles ?? []).map((r) => ({ value: r.name, label: r.name }));

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6">
      <PageHeader
        title="Usuários"
        subtitle={
          query.data
            ? `${items.length} cadastrado(s) · ${visible.length} em exibição`
            : "Equipe, papéis e salários"
        }
        className="mb-4"
        actions={
          me?.is_superadmin && (
            <Button asChild size="sm">
              <Link to="/admin/usuarios/novo">+ Novo usuário</Link>
            </Button>
          )
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          className={`${INPUT} min-w-56 flex-1`}
          placeholder="Buscar por nome ou email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Buscar usuário"
        />
        <FilterDropdown label="Papel" count={roles.length}>
          <CheckboxList
            options={roleOptions}
            selected={roles}
            onToggle={(v) => setRoles((prev) => toggle(prev, v))}
            searchable
            emptyMessage="Nenhum papel cadastrado."
          />
        </FilterDropdown>
        <FilterDropdown label="Situação" count={situations.length}>
          <CheckboxList
            options={SITUATION_OPTIONS}
            selected={situations}
            onToggle={(v) => setSituations((prev) => toggle(prev, v))}
          />
        </FilterDropdown>
        <FilterDropdown label="Pagamento" count={payments.length}>
          <CheckboxList
            options={PAYMENT_OPTIONS}
            selected={payments}
            onToggle={(v) => setPayments((prev) => toggle(prev, v))}
          />
        </FilterDropdown>
        <select
          className={INPUT}
          value={sort}
          onChange={(e) => setSort(e.target.value as SortKey)}
          aria-label="Ordenar usuários"
        >
          {Object.entries(SORT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {activeFilters > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch("");
              setRoles([]);
              setSituations([]);
              setPayments([]);
            }}
          >
            Limpar filtros
          </Button>
        )}
      </div>

      {query.data && (
        <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryTile label="Em exibição" value={String(visible.length)} />
          <SummaryTile label="Ativos" value={String(totals.active)} />
          <SummaryTile label="Com acesso" value={String(totals.withAccess)} />
          <SummaryTile
            label="Folha do mês"
            value={`R$ ${formatBRL(totals.payroll)}`}
            hint={`semanal × ${mondays} segunda(s) + quinzenal × 2`}
          />
        </div>
      )}

      {query.isLoading && (
        <div className="space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os usuários.
        </div>
      )}

      {query.data &&
        (visible.length === 0 ? (
          <p className="rounded-md border border-line bg-panel px-4 py-6 text-center text-sm text-muted">
            Nenhum usuário encontrado com esses filtros.
          </p>
        ) : (
          <div className="rounded-md border border-line bg-panel">
            <Table>
              <thead>
                <TableRow head>
                  <TableCell as="th">Nome</TableCell>
                  <TableCell as="th" className="hidden md:table-cell">
                    Papéis
                  </TableCell>
                  <TableCell as="th">Vínculo</TableCell>
                  <TableCell as="th" className="hidden lg:table-cell">
                    Frequência
                  </TableCell>
                  <TableCell as="th" align="right">
                    Salário
                  </TableCell>
                  <TableCell as="th" className="hidden xl:table-cell">
                    PIX
                  </TableCell>
                </TableRow>
              </thead>
              <tbody>
                {visible.map((user) => (
                  <UserRow key={user.id} user={user} />
                ))}
              </tbody>
            </Table>
          </div>
        ))}
    </div>
  );
}
