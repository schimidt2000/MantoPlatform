import { Link } from "react-router-dom";
import { Button, Card, CardContent } from "@manto/ui";

/** Confirmação de envio — paridade com `app/templates/cadastro/success.html`. */
export function CadastroSucessoPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-10">
      <Card className="w-full p-4 text-center">
        <CardContent className="flex flex-col items-center gap-3 pt-4">
          <div className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-accent text-3xl text-white">
            ✓
          </div>
          <h1 className="font-display text-xl text-accent-dark">Cadastro enviado!</h1>
          <p className="text-sm text-muted">Recebemos seus dados e suas fotos com sucesso.</p>
          <p className="text-sm text-muted">
            Nossa equipe vai analisar o seu cadastro. Obrigado pelo interesse em fazer parte da
            Manto Produções! 💜
          </p>
          <Button asChild className="mt-2">
            <Link to="/cadastro">Fazer outro cadastro</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
