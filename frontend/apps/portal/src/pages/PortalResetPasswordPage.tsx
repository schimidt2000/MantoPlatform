import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useParams } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { Button, Skeleton } from "@manto/ui";
import { AuthCard, AuthLink } from "../components/AuthCard";
import { FormError, FormField } from "../components/FormField";
import { PasswordChecklist } from "../components/PasswordChecklist";
import { useResetPassword, useResetTokenCheck } from "../lib/portalAccount";
import { newPasswordSchema, type NewPasswordForm } from "../lib/passwordSchema";

/** Redefinição de senha a partir do token enviado por e-mail (`/reset-password/:token`). */
export function PortalResetPasswordPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const tokenCheck = useResetTokenCheck(token);
  const resetPassword = useResetPassword();
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<NewPasswordForm>({ resolver: zodResolver(newPasswordSchema) });

  const password = watch("new_password") ?? "";

  const onSubmit = handleSubmit((values) => {
    setFormError(null);
    resetPassword.mutate(
      { ...values, token: token ?? "" },
      {
        onSuccess: () => setDone(true),
        onError: (error) => setFormError(error.message),
      },
    );
  });

  if (tokenCheck.isLoading) {
    return (
      <AuthCard title="Redefinir senha">
        <div className="space-y-3">
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      </AuthCard>
    );
  }

  if (tokenCheck.isError || !tokenCheck.data?.valid) {
    return (
      <AuthCard
        title="Link inválido"
        footer={<AuthLink to="/forgot-password">Pedir um novo link</AuthLink>}
      >
        <p className="text-sm text-ink">
          Este link de redefinição é inválido ou já expirou. Peça um novo — os links valem 1 hora.
        </p>
      </AuthCard>
    );
  }

  if (done) {
    return (
      <AuthCard title="Senha redefinida">
        <div className="space-y-4 text-sm text-ink">
          <CheckCircle2 className="h-10 w-10 text-green" aria-hidden="true" />
          <p>Tudo certo! Sua nova senha já está valendo.</p>
          <Button className="w-full" onClick={() => navigate("/login", { replace: true })}>
            Ir para o login
          </Button>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Redefinir senha" subtitle="Escolha uma senha nova para sua conta.">
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormField
          label="Nova senha"
          type="password"
          autoComplete="new-password"
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <PasswordChecklist password={password} />
        <FormField
          label="Repita a nova senha"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register("confirm_password")}
        />

        <FormError>{formError}</FormError>

        <Button type="submit" loading={resetPassword.isPending} className="w-full">
          Salvar nova senha
        </Button>
      </form>
    </AuthCard>
  );
}
