import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MailCheck } from "lucide-react";
import { Button } from "@manto/ui";
import { AuthCard, AuthLink } from "../components/AuthCard";
import { FormError, FormField } from "../components/FormField";
import { useForgotPassword } from "../lib/portalAccount";

const schema = z.object({
  login: z.string().min(1, "Informe seu CPF ou e-mail"),
  email: z.string().email("Informe um e-mail válido"),
});

type ForgotForm = z.infer<typeof schema>;

/**
 * Esqueci minha senha. O backend responde 200 mesmo quando o CPF não existe (não revela conta),
 * então a tela sempre mostra a mesma confirmação neutra.
 */
export function PortalForgotPasswordPage() {
  const forgot = useForgotPassword();
  const [formError, setFormError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotForm>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit((values) => {
    setFormError(null);
    forgot.mutate(values, {
      onSuccess: () => setSent(true),
      onError: (error) => setFormError(error.message),
    });
  });

  if (sent) {
    return (
      <AuthCard title="Verifique seu e-mail" footer={<AuthLink to="/login">Voltar ao login</AuthLink>}>
        <div className="space-y-3 text-sm text-ink">
          <MailCheck className="h-10 w-10 text-green" aria-hidden="true" />
          <p>
            Se o CPF e o e-mail conferem com o seu cadastro, enviamos um link para redefinir a
            senha. O link vale por 1 hora.
          </p>
          <p className="text-muted">Confira também a caixa de spam.</p>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Esqueci minha senha"
      subtitle="Confirme seu CPF e o e-mail cadastrado para receber o link de redefinição."
      footer={
        <>
          Lembrou a senha? <AuthLink to="/login">Entrar</AuthLink>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormField
          label="CPF ou e-mail"
          type="text"
          autoComplete="username"
          error={errors.login?.message}
          {...register("login")}
        />
        <FormField
          label="E-mail cadastrado"
          type="email"
          inputMode="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />

        <FormError>{formError}</FormError>

        <Button type="submit" loading={forgot.isPending} className="w-full">
          Enviar link de redefinição
        </Button>
      </form>
    </AuthCard>
  );
}
