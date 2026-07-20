import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, useReducedMotion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { useLogin } from "../lib/useAuth";

const loginSchema = z.object({
  email: z.string().min(1, "Informe o e-mail").email("E-mail inválido"),
  password: z.string().min(1, "Informe a senha"),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();
  const reduceMotion = useReducedMotion();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit((values) => {
    setFormError(null);
    login.mutate(values, {
      onSuccess: () => navigate("/", { replace: true }),
      onError: (error) => {
        // Erro com campos específicos (400) volta para o campo; senão, mensagem geral.
        if (error instanceof ApiRequestError && error.fields) {
          for (const [field, message] of Object.entries(error.fields)) {
            if (field === "email" || field === "password") {
              setError(field, { message });
            }
          }
          return;
        }
        setFormError(error.message);
      },
    });
  });

  return (
    <div className="flex min-h-full items-center justify-center bg-bg p-4">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="w-full max-w-sm"
      >
        <Card>
          <CardHeader>
            <CardTitle>Plataforma Manto</CardTitle>
            <p className="text-sm text-muted">Entre com suas credenciais.</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} noValidate className="space-y-4">
              <div className="space-y-1">
                <label htmlFor="email" className="text-sm font-medium text-ink">
                  E-mail
                </label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  aria-invalid={errors.email ? true : undefined}
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-sm text-red" role="alert">
                    {errors.email.message}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label htmlFor="password" className="text-sm font-medium text-ink">
                  Senha
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={errors.password ? true : undefined}
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-sm text-red" role="alert">
                    {errors.password.message}
                  </p>
                )}
              </div>

              {formError && (
                <div className="rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
                  {formError}
                </div>
              )}

              <Button type="submit" loading={login.isPending} className="w-full">
                {login.isPending ? "Entrando..." : "Entrar"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
