import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { formatBRL } from "@manto/money";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import {
  useAddSalary,
  useAdminUser,
  useDeleteAdminUser,
  useGrantAccess,
  useResetPassword,
  useUpdateAdminUserIdentity,
  useUpdatePix,
} from "../lib/adminUsers";
import { useCurrentUser } from "../lib/useAuth";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR");
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
  const [salaryAmount, setSalaryAmount] = useState("");
  const [salaryType, setSalaryType] = useState("");
  const [grantEmail, setGrantEmail] = useState("");
  const [grantPassword, setGrantPassword] = useState("");
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [identityErrors, setIdentityErrors] = useState<Record<string, string>>({});
  const [salaryError, setSalaryError] = useState<string | null>(null);

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

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-2xl p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o usuário.
        </div>
      </div>
    );
  }

  const user = query.data;

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/admin/usuarios">‹ Usuários</Link>
      </Button>

      <PageHeader
        title={user.name}
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
          {deleteUser.error instanceof ApiRequestError
            ? deleteUser.error.message
            : "Não foi possível excluir o usuário."}
        </p>
      )}

      {isSuperadmin && (
        <Card>
          <CardHeader>
            <CardTitle>Identidade e papéis</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className={LABEL}>Nome</label>
              <input className={INPUT} value={name} onChange={(e) => setName(e.target.value)} />
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
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className={LABEL}>Novo valor</label>
              <input
                className={INPUT}
                value={salaryAmount}
                onChange={(e) => setSalaryAmount(e.target.value)}
                placeholder="0,00"
              />
            </div>
            <div>
              <label className={LABEL}>Tipo de pagamento</label>
              <select
                className={INPUT}
                value={salaryType}
                onChange={(e) => setSalaryType(e.target.value)}
              >
                <option value="">Selecione…</option>
                <option value="semanal">Semanal</option>
                <option value="quinzenal">Quinzenal</option>
                <option value="comissao">Somente comissão</option>
              </select>
            </div>
          </div>
          {salaryError && <p className="text-xs text-red">{salaryError}</p>}
          <Button
            size="sm"
            loading={addSalary.isPending}
            onClick={() => {
              setSalaryError(null);
              addSalary.mutate(
                { amount: salaryAmount, payment_type: salaryType },
                {
                  onSuccess: () => {
                    setSalaryAmount("");
                    setSalaryType("");
                  },
                  onError: (err) => {
                    setSalaryError(
                      err instanceof ApiRequestError
                        ? err.message
                        : "Não foi possível registrar o salário.",
                    );
                  },
                },
              );
            }}
          >
            Registrar salário
          </Button>
          {user.salary_history.length > 0 && (
            <ul className="divide-y divide-line text-sm">
              {user.salary_history.map((h) => (
                <li key={h.id} className="flex justify-between gap-2 py-1.5">
                  <span className="text-ink">
                    R$ {formatBRL(h.amount)} ({h.payment_type})
                  </span>
                  <span className="text-muted">
                    {formatDate(h.start_date)} – {h.end_date ? formatDate(h.end_date) : "vigente"}
                  </span>
                </li>
              ))}
            </ul>
          )}
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
                {grantAccess.error instanceof ApiRequestError
                  ? grantAccess.error.message
                  : "Não foi possível conceder acesso."}
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
  );
}
