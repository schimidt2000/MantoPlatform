import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Button, Card, CardContent } from "@manto/ui";
import { suggestEmailCorrection, useResendConfirmation } from "../lib/cadastro";

interface SubmitState {
  id?: number | null;
  email?: string;
  token?: string;
}

/**
 * Confirmação de envio — paridade com `app/templates/cadastro/success.html`.
 *
 * Feature 219: o cadastro **já está gravado** quando esta tela aparece. Por isso a confirmação de
 * email mora aqui e não antes do envio — corrigir o endereço custa um campo, e não refazer as
 * fotos, o documento e o formulário inteiro.
 */
export function CadastroSucessoPage() {
  const state = (useLocation().state ?? {}) as SubmitState;
  const resend = useResendConfirmation();

  const [email, setEmail] = useState(state.email ?? "");
  const [token, setToken] = useState(state.token ?? "");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(state.email ?? "");
  const [done, setDone] = useState<string | null>(null);

  // Sem `state` (recarregou a página ou entrou pelo link direto) não há credencial para corrigir
  // nada — a tela vira o "cadastro enviado" simples de sempre.
  const canFix = Boolean(state.id && token);
  const draftTypo = suggestEmailCorrection(draft);

  const submit = (novoEmail?: string) => {
    setDone(null);
    resend.mutate(
      { id: state.id as number, token, email: novoEmail },
      {
        onSuccess: (result) => {
          setEmail(result.email);
          setToken(result.verify_token);
          setEditing(false);
          setDone(
            novoEmail
              ? `Pronto! Reenviamos para ${result.email}.`
              : `Reenviado para ${result.email}.`,
          );
        },
      },
    );
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-10">
      <Card className="w-full p-4 text-center">
        <CardContent className="flex flex-col items-center gap-3 pt-4">
          <div className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-accent text-3xl text-white">
            ✓
          </div>
          <h1 className="font-display text-xl text-accent-dark">Cadastro enviado!</h1>
          <p className="text-sm text-muted">Recebemos seus dados e suas fotos com sucesso.</p>

          {canFix ? (
            <>
              <div className="w-full rounded-md border border-line bg-surface-2 p-3 text-left">
                <p className="text-sm text-ink">
                  Enviamos um email de confirmação para{" "}
                  <strong className="break-all">{email}</strong>.
                </p>
                <p className="mt-1 text-xs text-muted">
                  Confirme para garantir que você vai receber nossos convites de trabalho. Seu
                  cadastro já está salvo — isso não se perde.
                </p>

                {editing ? (
                  <div className="mt-3 space-y-2">
                    <label className="block text-xs font-medium text-muted">
                      Corrigir o e-mail
                    </label>
                    <input
                      type="email"
                      className="h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      autoFocus
                    />
                    {draftTypo && (
                      <button
                        type="button"
                        onClick={() => setDraft(draftTypo)}
                        className="text-xs font-medium text-accent-dark underline"
                      >
                        Você quis dizer <strong>{draftTypo}</strong>?
                      </button>
                    )}
                    {resend.isError && (
                      <p className="text-xs text-red">
                        Não foi possível atualizar. Confira o endereço e tente de novo.
                      </p>
                    )}
                    <div className="flex gap-2">
                      <Button size="sm" loading={resend.isPending} onClick={() => submit(draft)}>
                        Salvar e reenviar
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
                        Cancelar
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setDraft(email);
                        setEditing(true);
                      }}
                    >
                      Esse e-mail está errado
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={resend.isPending}
                      onClick={() => submit()}
                    >
                      Reenviar
                    </Button>
                  </div>
                )}

                {done && <p className="mt-2 text-xs text-green">{done}</p>}
              </div>
              <p className="text-sm text-muted">
                Nossa equipe vai analisar o seu cadastro. Obrigado pelo interesse em fazer parte da
                Manto Produções! 💜
              </p>
            </>
          ) : (
            <p className="text-sm text-muted">
              Nossa equipe vai analisar o seu cadastro. Obrigado pelo interesse em fazer parte da
              Manto Produções! 💜
            </p>
          )}

          <Button asChild className="mt-2">
            <Link to="/cadastro">Fazer outro cadastro</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
