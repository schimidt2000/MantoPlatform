import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, useReducedMotion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@manto/ui";
import { usePortalLogin } from "../lib/portalAuth";

const loginSchema = z.object({
  login: z.string().min(1, "Informe seu CPF ou e-mail"),
  password: z.string().min(1, "Informe a senha"),
});

type LoginForm = z.infer<typeof loginSchema>;

export function PortalLoginPage() {
  const navigate = useNavigate();
  const login = usePortalLogin();
  const reduceMotion = useReducedMotion();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit((values) => {
    setFormError(null);
    login.mutate(values, {
      onSuccess: (talent) => {
        if (talent.must_redirect_to_classic) {
          // Troca de senha/termos pendentes: fora do escopo deste app — página inteira,
          // não navegação SPA, para cair na versão clássica (research.md §2).
          window.location.href = "/portal/login";
          return;
        }
        navigate("/agenda", { replace: true });
      },
      onError: (error) => setFormError(error.message),
    });
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg p-4">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="w-full max-w-sm"
      >
        <Card>
          <CardHeader>
            <CardTitle>Portal do Artista</CardTitle>
            <p className="text-sm text-muted">Entre com seu CPF (ou e-mail) e senha.</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} noValidate className="space-y-4">
              <div className="space-y-1">
                <label htmlFor="login" className="text-sm font-medium text-ink">
                  CPF ou e-mail
                </label>
                <Input
                  id="login"
                  type="text"
                  autoComplete="username"
                  inputMode="text"
                  aria-invalid={errors.login ? true : undefined}
                  {...register("login")}
                />
                {errors.login && (
                  <p className="text-sm text-red" role="alert">
                    {errors.login.message}
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
                Entrar
              </Button>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
