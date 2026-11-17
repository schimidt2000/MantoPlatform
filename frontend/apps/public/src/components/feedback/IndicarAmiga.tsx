import { Button } from "@manto/ui";
import { whatsappLink } from "../../lib/lojaTema";

/**
 * Feature 350: "Indicar uma amiga" abre o WhatsApp de quem avaliou com a mensagem pronta — o nome de
 * quem indica e o WhatsApp da Manto. Nenhum dado da amiga passa por aqui (ela não consentiu); a
 * vendedora marca "Indicado por" na ficha quando a amiga chegar.
 */
export function IndicarAmiga({ primeiroNome }: { primeiroNome: string | null }) {
  const assinatura = primeiroNome ? `indicação de ${primeiroNome}` : "indicação minha";
  const mensagem =
    "Oi! Fiz uma festa com a Manto Produções e recomendo muito. " +
    `Se você for fazer uma festa, fale com eles e diga que foi ${assinatura}: ${whatsappLink()}`;
  return (
    <div className="mt-2 w-full space-y-2">
      <p className="text-sm text-ink">Conhece alguém que vai fazer festa?</p>
      <Button asChild size="lg" variant="outline" className="w-full">
        <a
          href={`https://wa.me/?text=${encodeURIComponent(mensagem)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          💌 Indicar uma amiga
        </a>
      </Button>
    </div>
  );
}
