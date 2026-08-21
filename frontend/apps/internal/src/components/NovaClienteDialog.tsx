import { useState } from "react";
import { Link } from "react-router-dom";
import { UserPlus } from "lucide-react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
} from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { useQuickCreateClient, type QuickCreateClientResult } from "../lib/clientes";

function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiRequestError ? error.fields?.[field] : undefined;
}

function Campo({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-muted">{label}</span>
      {children}
      {error ? (
        <span className="mt-1 block text-xs text-red">{error}</span>
      ) : (
        hint && <span className="mt-1 block text-xs text-muted">{hint}</span>
      )}
    </label>
  );
}

/**
 * Cadastro manual de cliente na tela de Clientes (feature 258).
 *
 * Usa o MESMO endpoint do cadastro rápido do formulário de evento
 * (`POST /api/clientes/quick-create`, feature 165) — inclusive a regra de telefone único: se o
 * número já pertence a alguém, o servidor devolve o cliente existente com `reused: true` e nada
 * é criado. Aqui isso vira um aviso com atalho para a ficha dela, em vez de um cadastro
 * duplicado silencioso.
 *
 * Diferença para o cadastro do evento: aqui cabem CPF/CNPJ e endereço, porque quem cadastra pela
 * tela de Clientes normalmente está com o contrato ou a nota na mão.
 */
export function NovaClienteDialog({ onCreated }: { onCreated?: (id: number) => void }) {
  const [open, setOpen] = useState(false);
  const [resultado, setResultado] = useState<QuickCreateClientResult | null>(null);
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    company: "",
    cpf: "",
    cnpj: "",
    address: "",
  });
  const [erros, setErros] = useState<{ name?: string; phone?: string }>({});
  const criar = useQuickCreateClient();

  const patch = (campo: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((atual) => ({ ...atual, [campo]: e.target.value }));

  function fechar() {
    setOpen(false);
    // Só limpa depois da animação de saída, senão o formulário "pisca" vazio ao fechar.
    window.setTimeout(() => {
      setForm({ name: "", phone: "", email: "", company: "", cpf: "", cnpj: "", address: "" });
      setErros({});
      setResultado(null);
      criar.reset();
    }, 200);
  }

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    const faltando: { name?: string; phone?: string } = {};
    if (!form.name.trim()) faltando.name = "Informe o nome da cliente.";
    if (!form.phone.trim()) faltando.phone = "Informe o telefone com DDD.";
    setErros(faltando);
    if (faltando.name || faltando.phone) return;

    criar.mutate(
      {
        name: form.name.trim(),
        phone: form.phone.trim(),
        phone_display: form.phone.trim(),
        email: form.email.trim() || undefined,
        company: form.company.trim() || undefined,
        cpf: form.cpf.trim() || undefined,
        cnpj: form.cnpj.trim() || undefined,
        address: form.address.trim() || undefined,
      },
      {
        onSuccess: (cliente) => {
          setResultado(cliente);
          if (!cliente.reused) onCreated?.(cliente.id);
        },
      },
    );
  }

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <UserPlus className="mr-1.5 h-4 w-4" aria-hidden />
        Nova cliente
      </Button>

      <Dialog open={open} onOpenChange={(aberto) => (aberto ? setOpen(true) : fechar())}>
        <DialogContent open={open} className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{resultado ? "Cliente cadastrada" : "Nova cliente"}</DialogTitle>
            <DialogDescription>
              {resultado
                ? resultado.reused
                  ? "Esse telefone já estava cadastrado — nada foi duplicado."
                  : "Pronto. A ficha já está na base de clientes."
                : "Nome e telefone são obrigatórios; o resto pode ser completado depois na ficha."}
            </DialogDescription>
          </DialogHeader>

          {resultado ? (
            <div className="space-y-3">
              <div className="rounded-md border border-line bg-surface px-3 py-2 text-sm">
                <p className="font-medium text-ink">{resultado.name}</p>
                <p className="text-muted">
                  {[resultado.phone_display, resultado.company, resultado.email]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              {resultado.reused && (
                <p className="text-sm text-muted">
                  O telefone informado já pertence a esta ficha. Se for outra pessoa, confira o
                  número; se for a mesma, complete os dados direto na ficha dela.
                </p>
              )}
              <DialogFooter>
                <Button variant="ghost" onClick={fechar}>
                  Fechar
                </Button>
                <Button asChild>
                  <Link to={`/clientes/${resultado.id}`}>Abrir ficha</Link>
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <form className="space-y-3" onSubmit={enviar}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Campo label="Nome *" error={erros.name ?? fieldError(criar.error, "name")}>
                  <Input
                    value={form.name}
                    onChange={patch("name")}
                    aria-label="Nome da cliente"
                    aria-invalid={Boolean(erros.name ?? fieldError(criar.error, "name"))}
                    autoFocus
                  />
                </Campo>
                <Campo
                  label="Telefone com DDD *"
                  hint="Com DDI se for de fora do Brasil."
                  error={erros.phone ?? fieldError(criar.error, "phone")}
                >
                  <Input
                    value={form.phone}
                    onChange={patch("phone")}
                    placeholder="(11) 98765-4321"
                    aria-label="Telefone com DDD"
                    aria-invalid={Boolean(erros.phone ?? fieldError(criar.error, "phone"))}
                  />
                </Campo>
                <Campo label="E-mail">
                  <Input type="email" value={form.email} onChange={patch("email")} aria-label="E-mail" />
                </Campo>
                <Campo label="Empresa">
                  <Input value={form.company} onChange={patch("company")} aria-label="Empresa" />
                </Campo>
                <Campo label="CPF">
                  <Input value={form.cpf} onChange={patch("cpf")} aria-label="CPF" />
                </Campo>
                <Campo label="CNPJ">
                  <Input value={form.cnpj} onChange={patch("cnpj")} aria-label="CNPJ" />
                </Campo>
              </div>
              <Campo label="Endereço">
                <textarea
                  className="min-h-16 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
                  value={form.address}
                  onChange={patch("address")}
                  aria-label="Endereço"
                />
              </Campo>

              {criar.isError && !fieldError(criar.error, "name") && !fieldError(criar.error, "phone") && (
                <p className="text-sm text-red" role="alert">
                  Não foi possível cadastrar a cliente. Tente novamente em instantes.
                </p>
              )}

              <DialogFooter>
                <Button type="button" variant="ghost" onClick={fechar}>
                  Cancelar
                </Button>
                <Button type="submit" loading={criar.isPending}>
                  Cadastrar
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
