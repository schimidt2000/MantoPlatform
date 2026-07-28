import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MailCheck } from "lucide-react";
import { Button } from "@manto/ui";
import { AuthCard, AuthLink } from "../components/AuthCard";
import { FormError, FormField } from "../components/FormField";
import { useFirstAccess } from "../lib/portalAccount";

const schema = z.object({
  login: z.string().min(1, "Informe seu CPF ou e-mail"),
});

type FirstAccessForm = z.infer<typeof schema>;

/** Primeiro acesso: o talento pede a senha temporária que chega no e-mail cadastrado. */
export function PortalFirstAccessPage() {
  const firstAccess = useFirstAccess();
  const [formError, setFormError] = useState<string | null>(null);
  const [emailHint, setEmailHint] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FirstAccessForm>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit((values) => {
    setFormError(null);
    firstAccess.mutate(values, {
      onSuccess: (result) => setEmailHint(result.email_hint),
      onError: (error) => setFormError(error.message),
    });
  });

  if (emailHint) {
    return (
      <AuthCard
        title="Senha enviada"
        footer={<AuthLink to="/login">Ir para o login</AuthLink>}
      >
        <div className="space-y-3 text-sm text-ink">
          <MailCheck className="h-10 w-10 text-green" aria-hidden="true" />
          <p>
            Enviamos uma senha temporária para <strong>{emailHint}</strong>.
          </p>
          <p className="text-muted">
            Confira também a caixa de spam. Ao entrar, você vai criar sua senha definitiva.
          </p>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Primeiro acesso"
      subtitle="Informe seu CPF (ou e-mail) e enviaremos uma senha temporária."
      footer={
        <>
          Já tem senha? <AuthLink to="/login">Entrar</AuthLink>
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

        <FormError>{formError}</FormError>

        <Button type="submit" loading={firstAccess.isPending} className="w-full">
          Enviar senha temporária
        </Button>
      </form>
    </AuthCard>
  );
}
