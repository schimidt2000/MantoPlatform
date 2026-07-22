import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@manto/ui";
import { useAdminUsers, useCreateAdminUser } from "../lib/adminUsers";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

export function AdminUserCreatePage() {
  const navigate = useNavigate();
  const rolesQuery = useAdminUsers();
  const create = useCreateAdminUser();

  const [userType, setUserType] = useState<"access" | "payment_only">("access");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [tempPassword, setTempPassword] = useState("");
  const [roleIds, setRoleIds] = useState<number[]>([]);
  const [pixKey, setPixKey] = useState("");
  const [pixKeyType, setPixKeyType] = useState("");
  const [salaryAmount, setSalaryAmount] = useState("");
  const [salaryType, setSalaryType] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const toggleRole = (id: number) =>
    setRoleIds((prev) => (prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]));

  const handleSubmit = () => {
    setFieldErrors({});
    create.mutate(
      {
        user_type: userType,
        name,
        email: email || undefined,
        temp_password: userType === "access" ? tempPassword : undefined,
        role_ids: userType === "access" ? roleIds : undefined,
        pix_key: pixKey || undefined,
        pix_key_type: pixKeyType || undefined,
        salary:
          salaryAmount || salaryType
            ? { amount: salaryAmount, payment_type: salaryType }
            : undefined,
      },
      {
        onSuccess: () => navigate("/admin/usuarios"),
        onError: (err) => {
          if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
        },
      },
    );
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/admin/usuarios">‹ Usuários</Link>
      </Button>

      <header>
        <h1 className="text-2xl font-semibold text-ink">Novo usuário</h1>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Identidade</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <button
              type="button"
              className={`rounded-md border px-3 py-1.5 text-sm ${userType === "access" ? "border-accent bg-accent-soft text-accent-dark" : "border-line text-ink"}`}
              onClick={() => setUserType("access")}
            >
              Com acesso ao sistema
            </button>
            <button
              type="button"
              className={`rounded-md border px-3 py-1.5 text-sm ${userType === "payment_only" ? "border-accent bg-accent-soft text-accent-dark" : "border-line text-ink"}`}
              onClick={() => setUserType("payment_only")}
            >
              Só pagamento (sem login)
            </button>
          </div>
          <div>
            <label className={LABEL}>Nome</label>
            <input className={INPUT} value={name} onChange={(e) => setName(e.target.value)} />
            {fieldErrors.name && <p className="mt-1 text-xs text-red">{fieldErrors.name}</p>}
          </div>
          <div>
            <label className={LABEL}>
              Email{userType === "access" ? "" : " (opcional)"}
            </label>
            <input
              type="email"
              className={INPUT}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {fieldErrors.email && <p className="mt-1 text-xs text-red">{fieldErrors.email}</p>}
          </div>
          {userType === "access" && (
            <>
              <div>
                <label className={LABEL}>Senha temporária</label>
                <input
                  type="text"
                  className={INPUT}
                  value={tempPassword}
                  onChange={(e) => setTempPassword(e.target.value)}
                />
              </div>
              {rolesQuery.data && rolesQuery.data.all_roles.length > 0 && (
                <div>
                  <label className={LABEL}>Papéis</label>
                  <div className="flex flex-wrap gap-1.5">
                    {rolesQuery.data.all_roles.map((r) => (
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
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>PIX (opcional)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Chave PIX</label>
            <input className={INPUT} value={pixKey} onChange={(e) => setPixKey(e.target.value)} />
          </div>
          <div>
            <label className={LABEL}>Tipo de chave</label>
            <input
              className={INPUT}
              value={pixKeyType}
              onChange={(e) => setPixKeyType(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Salário (opcional)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Valor</label>
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
          {fieldErrors.salary && (
            <p className="text-xs text-red sm:col-span-2">{fieldErrors.salary}</p>
          )}
        </CardContent>
      </Card>

      <Button loading={create.isPending} onClick={handleSubmit}>
        Criar usuário
      </Button>
      {create.isError && !Object.keys(fieldErrors).length && (
        <p className="text-sm text-red">Não foi possível criar o usuário.</p>
      )}
    </div>
  );
}
