import { useParams } from "react-router-dom";
import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { useConfirmEmail } from "../lib/cadastro";

/**
 * Destino do link "Confirmar meu email" (feature 219).
 *
 * Confirmar consome o token, então clicar duas vezes cai em 404 — a tela trata isso como "link já
 * usado", não como erro, porque do ponto de vista de quem clicou já está tudo certo.
 */
export function CadastroConfirmarPage() {
  const { token } = useParams<{ token: string }>();
  const confirm = useConfirmEmail(token);

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-10">
      <Card className="w-full p-4 text-center">
        <CardContent className="flex flex-col items-center gap-3 pt-4">
          {confirm.isLoading && (
            <>
              <Skeleton className="h-[72px] w-[72px] rounded-full" />
              <Skeleton className="h-6 w-2/3" />
              <p className="text-sm text-muted">Confirmando seu email…</p>
            </>
          )}

          {confirm.isSuccess && (
            <>
              <div className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-accent text-3xl text-white">
                ✓
              </div>
              <h1 className="font-display text-xl text-accent-dark">E-mail confirmado!</h1>
              <p className="text-sm text-muted">
                Tudo certo, {confirm.data.name.split(" ")[0]}. Vamos usar{" "}
                <strong className="break-all">{confirm.data.email}</strong> para te avisar sobre os
                trabalhos.
              </p>
            </>
          )}

          {confirm.isError && (
            <>
              <div className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-surface-2 text-3xl">
                🔗
              </div>
              <h1 className="font-display text-xl text-ink">Link já utilizado</h1>
              <p className="text-sm text-muted">
                Este link de confirmação não vale mais — provavelmente porque você já confirmou.
                Se não foi o caso, fale com a equipe da Manto.
              </p>
            </>
          )}

          {/* Âncora absoluta, não `Link`: esta página é servida em DOIS endereços com basenames
              diferentes (`/cadastro/confirmar/:token` na raiz e `/catalogo/cadastro/confirmar/...`
              dos e-mails antigos). Um `to="/"` resolveria para a raiz do domínio no primeiro caso
              — que é o ERP interno, não o catálogo. */}
          <Button asChild variant="outline" className="mt-2">
            <a href={import.meta.env.PROD ? "/catalogo" : "/"}>Ver o catálogo da Manto</a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
