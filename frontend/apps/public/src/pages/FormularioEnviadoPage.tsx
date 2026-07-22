import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Card, CardContent, Button } from "@manto/ui";
import type { FormSubmitResult } from "../lib/formularios";

/** Confirmação de envio — paridade com `app/templates/formularios/enviado.html`. */
export function FormularioEnviadoPage() {
  const location = useLocation();
  const result = (location.state as FormSubmitResult | null) ?? { wa_link: null, contact_name: null };
  const firstName = result.contact_name?.split(" ")[0];

  useEffect(() => {
    if (!result.wa_link) return;
    const timer = setTimeout(() => {
      window.location.href = result.wa_link as string;
    }, 1200);
    return () => clearTimeout(timer);
  }, [result.wa_link]);

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-10">
      <Card className="w-full p-4 text-center">
        <CardContent className="flex flex-col items-center gap-3 pt-4">
          <div className="text-4xl">✅</div>
          <h1 className="font-display text-xl text-accent-dark">
            Recebemos suas informações{firstName ? `, ${firstName}` : ""}!
          </h1>
          {result.wa_link ? (
            <>
              <p className="text-sm text-muted">
                Falta só um passo: toque no botão abaixo para nos enviar a mensagem no WhatsApp
                com o resumo do seu pré-contrato.
              </p>
              <Button asChild className="mt-2 w-full">
                <a href={result.wa_link}>Enviar mensagem no WhatsApp</a>
              </Button>
              <p className="text-xs text-muted">
                O WhatsApp vai abrir com a mensagem pronta — é só confirmar o envio.
              </p>
            </>
          ) : (
            <p className="text-sm text-muted">Obrigado! Nossa equipe entrará em contato.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
