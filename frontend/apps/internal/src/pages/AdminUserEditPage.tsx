import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Pencil, Trash2 } from "lucide-react";
import { formatBRL, MoneyInput } from "@manto/money";
import { ApiRequestError } from "@manto/api-client";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import {
  useAddSalary,
  useAdminUser,
  useDeleteAdminUser,
  useDeleteSalary,
  useGrantAccess,
  useResetPassword,
  useUpdateAdminUserIdentity,
  useUpdatePix,
  useUpdateSalary,
  type SalaryHistoryEntry,
} from "../lib/adminUsers";
import { useCurrentUser } from "../lib/useAuth";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

const PAYMENT_TYPES = [
  { value: "semanal", label: "Semanal" },
  { value: "quinzenal", label: "Quinzenal" },
  { value: "comissao", label: "Somente comissão" },
];

function formatDate(iso: string | null): string {
  if (!iso) return "";
  // Data pura ("YYYY-MM-DD") — montada em horário local para não voltar um dia por fuso.
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("pt-BR");
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiRequestError ? error.message : fallback;
}

interface SalaryHistoryRowProps {
  entry: SalaryHistoryEntry;
  userId: number;
  canEdit: boolean;
  onResynced: (count: number) => void;
}

/**
 * Uma faixa do histórico salarial, com correção e exclusão inline (feature 218).
 *
 * Registrar um salário novo só corrige dali para a frente — um valor digitado errado continua no
 * histórico e na planilha de pagamentos do mês. Por isso o superadmin edita/exclui a faixa aqui, e
 * o backend realinha os lançamentos ainda não pagos.
 */
function SalaryHistoryRow({ entry, userId, canEdit, onResynced }: SalaryHistoryRowProps) {
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState(entry.amount);
  const [paymentType, setPaymentType] = useState(entry.payment_type);
  const [startDate, setStartDate] = useState(entry.start_date.slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  const updateSalary = useUpdateSalary(userId);
  const deleteSalary = useDeleteSalary(userId);
  const isCurrent = entry.end_date === null;

  const startEditing = () => {
    setAmount(entry.amount);
    setPaymentType(entry.payment_type);
    setStartDate(entry.start_date.slice(0, 10));
    setError(null);
    setEditing(true);
  };

  if (editing) {
    return (
      <li className="space-y-2 py-2">
        <div className="grid gap-2 sm:grid-cols-3">
          <div>
            <label className={LABEL}>Valor</label>
            <MoneyInput className={INPUT} value={amount} onValueChange={setAmount} />
          </div>
          <div>
            <label className={LABEL}>Tipo</label>
            <select
              className={INPUT}
              value={paymentType}
              onChange={(e) => setPaymentType(e.target.value)}
            >
              {PAYMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={LABEL}>Início</label>
            <input
              type="date"
              className={INPUT}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
        </div>
        {error && <p className="text-xs text-red">{error}</p>}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            loading={updateSalary.isPending}
            onClick={() => {
              setError(null);
              updateSalary.mutate(
                {
                  salaryId: entry.id,
                  amount: String(amount),
                  payment_type: paymentType,
                  start_date: startDate || undefined,
                },
                {
                  onSuccess: (result) => {
                    setEditing(false);
                    onResynced(result.payments_resynced);
                  },
                  onError: (err) =>
                    setError(errorMessage(err, "Não foi possível corrigir o salário.")),
                },
              );
            }}
          >
            Salvar correção
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
            Cancelar
          </Button>
        </div>
      </li>
    );
  }

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-2">
      <span className="text-ink">
        R$ {formatBRL(entry.amount)}{" "}
        <span className="text-muted">({entry.payment_type})</span>
        {isCurrent && (
          <Badge tone="green" className="ml-2">
            Vigente
          </Badge>
        )}
      </span>
      <span className="flex items-center gap-2">
        <span className="text-muted">
          {formatDate(entry.start_date)} – {entry.end_date ? formatDate(entry.end_date) : "hoje"}
        </span>
        {canEdit && (
          <>
            <button
              type="button"
              onClick={startEditing}
              title="Corrigir esta faixa"
              aria-label={`Corrigir salário de R$ ${formatBRL(entry.amount)}`}
              className="rounded p-1 text-muted transition-colors hover:bg-surface-2 hover:text-accent"
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden />
            </button>
            <button
              type="button"
              disabled={deleteSalary.isPending}
              onClick={() => {
                if (
                  !window.confirm(
                    `Excluir a faixa de R$ ${formatBRL(entry.amount)} (${entry.payment_type})?\n\n` +
                      "Os lançamentos ainda não pagos da planilha serão recalculados pelo salário " +
                      "que passar a valer no período. Os já pagos não mudam.",
                  )
                )
                  return;
                deleteSalary.mutate(entry.id, {
                  onSuccess: (result) => onResynced(result.payments_resynced),
                });
              }}
              title="Excluir esta faixa"
              aria-label={`Excluir salário de R$ ${formatBRL(entry.amount)}`}
              className="rounded p-1 text-muted transition-colors hover:bg-red-soft hover:text-red disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
            </button>
          </>
        )}
      </span>
    </li>
  );
}

export function AdminUserEditPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const navigate = useNavigate();
  const query = useAdminUser(id);
  const { data: me } = useCurrentUser();
  const isSuperadmin = Boolean(me?.is_superadmin);

  const updateIdentity = useUpdateAdminUserIdentity(id);
  const updatePix = useUpdatePix(id);
  const addSalary = useAddSalary(id);
  const grantAccess = useGrantAccess(id);
  const resetPassword = useResetPassword(id);
  const deleteUser = useDeleteAdminUser();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [receivesCommission, setReceivesCommission] = useState(true);
  const [roleIds, setRoleIds] = useState<number[]>([]);
  const [pixKey, setPixKey] = useState("");
  const [pixKeyType, setPixKeyType] = useState("");
  const [salaryAmount, setSalaryAmount] = useState(0);
  const [salaryType, setSalaryType] = useState("");
  const [salaryStart, setSalaryStart] = useState("");
  const [grantEmail, setGrantEmail] = useState("");
  const [grantPassword, setGrantPassword] = useState("");
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [identityErrors, setIdentityErrors] = useState<Record<string, string>>({});
  const [salaryError, setSalaryError] = useState<string | null>(null);
  const [resyncNotice, setResyncNotice] = useState<string | null>(null);

  useEffect(() => {
    if (query.data) {
      setName(query.data.name);
      setEmail(query.data.email);
      setIsActive(query.data.is_active);
      setReceivesCommission(query.data.receives_commission);
      setRoleIds(query.data.role_ids);
      setPixKey(query.data.pix_key);
      setPixKeyType(query.data.pix_key_type);
    }
  }, [query.data]);

  const toggleRole = (roleId: number) =>
    setRoleIds((prev) =>
      prev.includes(roleId) ? prev.filter((r) => r !== roleId) : [...prev, roleId],
    );

  const noticeFromResync = (count: number) =>
    setResyncNotice(
      count > 0
        ? `${count} lançamento(s) não pago(s) da planilha de pagamentos foram atualizados.`
        : "Histórico atualizado. Nenhum lançamento em aberto precisou mudar.",
    );

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-2/3" />
        <div className="grid gap-4 xl:grid-cols-2">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-[1400px] p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o usuário.
        </div>
      </div>
    );
  }

  const user = query.data;

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/admin/usuarios">‹ Usuários</Link>
      </Button>

      <PageHeader
        title={user.name}
        subtitle={`${user.email || "sem email"} · ${user.has_access ? "com acesso" : "só pagamento"}${
          user.is_active ? "" : " · inativo"
        }`}
        className="mb-0"
        actions={
          isSuperadmin && (
            <Button
              variant="outline"
              size="sm"
              loading={deleteUser.isPending}
              onClick={() => {
                if (window.confirm(`Excluir o usuário "${user.name}"?`)) {
                  deleteUser.mutate(id, { onSuccess: () => navigate("/admin/usuarios") });
                }
              }}
            >
              Excluir
            </Button>
          )
        }
      />
      {deleteUser.isError && (
        <p className="text-sm text-red">
          {errorMessage(deleteUser.error, "Não foi possível excluir o usuário.")}
        </p>
      )}

      {/* Duas colunas no desktop: cadastro à esquerda, dinheiro à direita — a ficha inteira cabe
          numa tela só em vez de virar uma pilha vertical de cards estreitos. */}
      <div className="grid items-start gap-4 [&>*]:min-w-0 xl:grid-cols-2">
        <div className="space-y-4">
          {isSuperadmin && (
            <Card>
              <CardHeader>
                <CardTitle>Identidade e papéis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className={LABEL}>Nome</label>
                    <input
                      className={INPUT}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                    {identityErrors.name && (
                      <p className="mt-1 text-xs text-red">{identityErrors.name}</p>
                    )}
                  </div>
                  <div>
                    <label className={LABEL}>Email</label>
                    <input
                      type="email"
                      className={INPUT}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                    {identityErrors.email && (
                      <p className="mt-1 text-xs text-red">{identityErrors.email}</p>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap gap-4">
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={(e) => setIsActive(e.target.checked)}
                    />
                    Usuário ativo
                  </label>
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={receivesCommission}
                      onChange={(e) => setReceivesCommission(e.target.checked)}
                    />
                    Recebe comissão
                  </label>
                </div>
                {user.has_access && user.all_roles.length > 0 && (
                  <div>
                    <label className={LABEL}>Papéis</label>
                    <div className="flex flex-wrap gap-1.5">
                      {user.all_roles.map((r) => (
                        <button
                          key={r.id}
                          type="button"
                          className={`rounded-md border px-2 py-1 text-xs ${roleIds.includes(r.id) ? "border-accent bg-accent-soft text-accent-dark" : "border-line text-ink"}`}
                          onClick={() => toggleRole(r.id)}
                        >
                          {r.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <Button
                  size="sm"
                  loading={updateIdentity.isPending}
                  onClick={() => {
                    setIdentityErrors({});
                    updateIdentity.mutate(
                      {
                        name,
                        email: email || undefined,
                        is_active: isActive,
                        receives_commission: receivesCommission,
                        role_ids: roleIds,
                      },
                      {
                        onError: (err) => {
                          if (err instanceof ApiRequestError && err.fields) {
                            setIdentityErrors(err.fields);
                          }
                        },
                      },
                    );
                  }}
                >
                  Salvar
                </Button>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>PIX</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className={LABEL}>Chave PIX</label>
                  <input
                    className={INPUT}
                    value={pixKey}
                    onChange={(e) => setPixKey(e.target.value)}
                  />
                </div>
                <div>
                  <label className={LABEL}>Tipo de chave</label>
                  <input
                    className={INPUT}
                    value={pixKeyType}
                    onChange={(e) => setPixKeyType(e.target.value)}
                  />
                </div>
              </div>
              <Button
                size="sm"
                loading={updatePix.isPending}
                onClick={() => updatePix.mutate({ pix_key: pixKey, pix_key_type: pixKeyType })}
              >
                Salvar PIX
              </Button>
            </CardContent>
          </Card>

          {isSuperadmin && !user.has_access && (
            <Card>
              <CardHeader>
                <CardTitle>Conceder acesso</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className={LABEL}>Email</label>
                    <input
                      type="email"
                      className={INPUT}
                      value={grantEmail}
                      onChange={(e) => setGrantEmail(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={LABEL}>Senha temporária</label>
                    <input
                      className={INPUT}
                      value={grantPassword}
                      onChange={(e) => setGrantPassword(e.target.value)}
                    />
                  </div>
                </div>
                {grantAccess.isError && (
                  <p className="text-xs text-red">
                    {errorMessage(grantAccess.error, "Não foi possível conceder acesso.")}
                  </p>
                )}
                <Button
                  size="sm"
                  loading={grantAccess.isPending}
                  onClick={() =>
                    grantAccess.mutate({ email: grantEmail, temp_password: grantPassword })
                  }
                >
                  Conceder acesso
                </Button>
              </CardContent>
            </Card>
          )}

          {isSuperadmin && user.has_access && (
            <Card>
              <CardHeader>
                <CardTitle>Resetar senha</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <input
                  className={INPUT}
                  placeholder="Nova senha temporária"
                  value={resetPasswordValue}
                  onChange={(e) => setResetPasswordValue(e.target.value)}
                />
                {resetPassword.isError && (
                  <p className="text-xs text-red">Não foi possível resetar a senha.</p>
                )}
                {resetPassword.isSuccess && (
                  <p className="text-xs text-green">Senha resetada com sucesso.</p>
                )}
                <Button
                  size="sm"
                  loading={resetPassword.isPending}
                  onClick={() => resetPassword.mutate(resetPasswordValue)}
                >
                  Resetar senha
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Salário</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {user.salary ? (
              <p className="text-sm text-ink">
                Vigente: R$ {formatBRL(user.salary.amount)} ({user.salary.payment_type}) desde{" "}
                {formatDate(user.salary.start_date)}
              </p>
            ) : (
              <p className="text-sm text-muted">Nenhum salário vigente.</p>
            )}

            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className={LABEL}>Novo valor</label>
                <MoneyInput className={INPUT} value={salaryAmount} onValueChange={setSalaryAmount} />
              </div>
              <div>
                <label className={LABEL}>Tipo de pagamento</label>
                <select
                  className={INPUT}
                  value={salaryType}
                  onChange={(e) => setSalaryType(e.target.value)}
                >
                  <option value="">Selecione…</option>
                  {PAYMENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={LABEL}>A partir de</label>
                <input
                  type="date"
                  className={INPUT}
                  value={salaryStart}
                  onChange={(e) => setSalaryStart(e.target.value)}
                />
              </div>
            </div>
            {salaryError && <p className="text-xs text-red">{salaryError}</p>}
            <Button
              size="sm"
              loading={addSalary.isPending}
              onClick={() => {
                setSalaryError(null);
                setResyncNotice(null);
                addSalary.mutate(
                  {
                    amount: String(salaryAmount),
                    payment_type: salaryType,
                    start_date: salaryStart || undefined,
                  },
                  {
                    onSuccess: () => {
                      setSalaryAmount(0);
                      setSalaryType("");
                      setSalaryStart("");
                    },
                    onError: (err) => {
                      setSalaryError(
                        errorMessage(err, "Não foi possível registrar o salário."),
                      );
                    },
                  },
                );
              }}
            >
              Registrar salário
            </Button>

            {resyncNotice && (
              <p className="rounded-md bg-green-soft px-3 py-2 text-xs text-green" role="status">
                {resyncNotice}
              </p>
            )}

            {user.salary_history.length > 0 && (
              <div className="space-y-1 pt-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
                    Histórico
                  </h3>
                  {isSuperadmin && (
                    <span className="text-[11px] text-muted">
                      Errou o valor? Corrija ou exclua a faixa aqui.
                    </span>
                  )}
                </div>
                <ul className="divide-y divide-line text-sm">
                  {user.salary_history.map((h) => (
                    <SalaryHistoryRow
                      key={h.id}
                      entry={h}
                      userId={id}
                      canEdit={isSuperadmin}
                      onResynced={noticeFromResync}
                    />
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
