import { Instagram, MessageCircle } from "lucide-react";
import { cn } from "@manto/ui";
import type { Canal } from "../../lib/conversas";

/**
 * O canal da conversa (feature 330): balão para o WhatsApp, a marca do Instagram para o Direct.
 * O nome do canal vai para leitor de tela; na tela fica só o ícone, ao lado do nome do contato.
 */

const ROTULO: Record<Canal, string> = { whatsapp: "WhatsApp", instagram: "Instagram" };

export function IconeDoCanal({ canal, className }: { canal: string; className?: string }) {
  const instagram = canal === "instagram";
  const Icone = instagram ? Instagram : MessageCircle;
  return (
    <span className={cn("inline-flex shrink-0 items-center", instagram ? "text-accent" : "text-green", className)}>
      <Icone className="h-3.5 w-3.5" aria-hidden />
      <span className="sr-only">{ROTULO[instagram ? "instagram" : "whatsapp"]}</span>
    </span>
  );
}
