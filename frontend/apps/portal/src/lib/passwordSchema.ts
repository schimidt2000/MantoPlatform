import { z } from "zod";

/**
 * Regras de força de senha do portal — espelho exato de `PASSWORD_RULES` em
 * `app/talent_portal/portal_account_ops.py`.
 *
 * A validação do servidor continua sendo a que vale; esta existe só para dar feedback imediato
 * antes do envio (Princípio V). Ao mudar uma regra, mude nos dois lados.
 */
export const PASSWORD_REQUIREMENTS: Array<{ test: (pw: string) => boolean; label: string }> = [
  { test: (pw) => pw.length >= 8, label: "Mínimo de 8 caracteres" },
  { test: (pw) => /[A-Z]/.test(pw), label: "1 letra maiúscula" },
  { test: (pw) => /[a-z]/.test(pw), label: "1 letra minúscula" },
  { test: (pw) => /[0-9]/.test(pw), label: "1 número" },
  { test: (pw) => /[^A-Za-z0-9]/.test(pw), label: "1 símbolo (ex.: @, #, !, %)" },
];

/** Schema de "senha nova + confirmação", com as mensagens em pt-BR do backend. */
export const newPasswordSchema = z
  .object({
    new_password: z
      .string()
      .min(8, "A senha deve ter pelo menos 8 caracteres.")
      .regex(/[A-Z]/, "A senha deve ter pelo menos 1 letra maiúscula.")
      .regex(/[a-z]/, "A senha deve ter pelo menos 1 letra minúscula.")
      .regex(/[0-9]/, "A senha deve ter pelo menos 1 número.")
      .regex(/[^A-Za-z0-9]/, "A senha deve ter pelo menos 1 símbolo (ex.: @, #, !, %)."),
    confirm_password: z.string().min(1, "Repita a senha."),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: "As senhas não coincidem.",
    path: ["confirm_password"],
  });

export type NewPasswordForm = z.infer<typeof newPasswordSchema>;
