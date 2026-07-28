import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@manto/ui";
import { AuthCard } from "../components/AuthCard";
import { FormError, FormField } from "../components/FormField";
import { PasswordChecklist } from "../components/PasswordChecklist";
import { useChangePassword } from "../lib/portalAccount";
import { newPasswordSchema, type NewPasswordForm } from "../lib/passwordSchema";

/**
 * Troca de senha obrigatória do primeiro acesso — etapa de onboarding servida pelo
 * `OnboardingGate`, não uma rota que o talento alcança sozinho.
 */
export function PortalChangePasswordPage() {
  const changePassword = useChangePassword();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<NewPasswordForm>({ resolver: zodResolver(newPasswordSchema) });

  const password = watch("new_password") ?? "";

  const onSubmit = handleSubmit((values) => {
    setFormError(null);
    // Sem `onSuccess` aqui: o hook atualiza o cache do talento e o `OnboardingGate` avança
    // sozinho para a próxima etapa pendente (ou libera o app).
    changePassword.mutate(values, { onError: (error) => setFormError(error.message) });
  });

  return (
    <AuthCard
      title="Crie sua senha"
      subtitle="Por segurança, defina uma senha própria antes de usar o portal."
    >
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

        <Button type="submit" loading={changePassword.isPending} className="w-full">
          Salvar e continuar
        </Button>
      </form>
    </AuthCard>
  );
}
