import { Check, X } from "lucide-react";
import { PASSWORD_REQUIREMENTS } from "../lib/passwordSchema";

/**
 * Checklist ao vivo das regras de senha — o talento vê o que falta antes de tentar enviar,
 * em vez de descobrir regra a regra a cada erro do servidor (Princípio V).
 */
export function PasswordChecklist({ password }: { password: string }) {
  return (
    <ul className="space-y-1" aria-label="Requisitos da senha">
      {PASSWORD_REQUIREMENTS.map(({ test, label }) => {
        const ok = test(password);
        const Icon = ok ? Check : X;
        return (
          <li
            key={label}
            className={`flex items-center gap-2 text-xs ${ok ? "text-green" : "text-muted"}`}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>{label}</span>
            <span className="sr-only">{ok ? "atendido" : "pendente"}</span>
          </li>
        );
      })}
    </ul>
  );
}
