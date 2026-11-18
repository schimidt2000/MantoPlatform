import { useState } from "react";
import { ExternalLink, MapPin } from "lucide-react";
import { cn } from "../lib/cn";
import { linksDeMapa } from "../lib/mapas";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./dialog";

export interface EnderecoNoMapaProps {
  /** O endereço como está gravado no evento. Vazio ou ausente: o componente não desenha nada. */
  endereco: string | null | undefined;
  /** Classes extras do gatilho — ex.: o alvo de 44px dos cards do portal. */
  className?: string;
}

/**
 * Endereço tocável que abre a escolha do app de mapas: Google Maps, Apple Mapas ou Waze
 * (feature 347). Uma peça só para o app interno e o portal, para os textos e a ordem não
 * divergirem entre as duas superfícies.
 *
 * A escolha é o `Dialog` do design system, não um menu suspenso: já traz Esc e toque fora
 * fechando, foco preso e devolvido ao endereço, e animação que respeita "reduzir movimento".
 *
 * Os links abrem com `target="_blank"` de propósito, ao contrário do arquivo do sistema
 * (`docs/00` §5): aqui o objetivo é SAIR para outro app. No iPhone com o sistema na Tela de
 * Início, o link universal entrega ao app de mapas; sem o app, abre o navegador, e o sistema
 * continua atrás, na mesma tela — o mesmo caminho que o link do WhatsApp já usa.
 */
function EnderecoNoMapa({ endereco, className }: EnderecoNoMapaProps) {
  const [aberto, setAberto] = useState(false);
  const opcoes = linksDeMapa(endereco);
  if (opcoes.length === 0) return null;
  const texto = (endereco ?? "").trim();

  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        <button
          type="button"
          title="Abrir no app de mapas"
          // O nome acessível começa pelo texto visível (WCAG 2.5.3): quem usa comando de voz diz
          // o que vê na tela.
          aria-label={`${texto} — abrir no app de mapas`}
          className={cn(
            "inline-flex min-w-0 items-start gap-1 rounded-sm text-left text-accent underline-offset-2 transition-colors hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            className,
          )}
        >
          <MapPin className="mt-[0.2em] h-[1em] w-[1em] shrink-0" aria-hidden="true" />
          <span className="min-w-0 break-words">{texto}</span>
        </button>
      </DialogTrigger>
      <DialogContent open={aberto}>
        <DialogHeader>
          <DialogTitle>Abrir endereço</DialogTitle>
          <DialogDescription className="break-words">{texto}</DialogDescription>
        </DialogHeader>
        <ul className="flex flex-col gap-2">
          {opcoes.map((opcao) => (
            <li key={opcao.app}>
              <a
                href={opcao.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setAberto(false)}
                className="flex min-h-[44px] items-center justify-between gap-3 rounded-md border border-line px-4 text-sm font-medium text-ink transition-colors hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {opcao.rotulo}
                <ExternalLink className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
              </a>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

export { EnderecoNoMapa };
