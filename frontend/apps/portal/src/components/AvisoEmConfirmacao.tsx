import { CircleAlert } from "lucide-react";

/**
 * "Evento em confirmação — entre em contato com a produção" (feature 303) — fonte única do aviso
 * para Agenda, Convites e Histórico.
 *
 * Aparece quando o evento sumiu do Google Agenda e a produção ainda não decidiu o que fazer com
 * ele. O artista escalado não precisa saber de Google: precisa saber que não deve contar com o
 * evento sem falar com a produção. Por isso a tela recebe só o booleano e escreve o texto aqui.
 *
 * Sem botão de dispensar e sem o mecanismo do "Ciente" (que zera o aviso de alteração): este
 * aviso dura enquanto a situação durar. Quebra linha em vez de cortar — a menor tela do portal é
 * 320 px.
 */
export function AvisoEmConfirmacao({ ativo }: { ativo?: boolean }) {
  if (!ativo) return null;
  return (
    <div
      role="note"
      className="flex w-full items-start gap-2 rounded-md bg-gold-soft px-3 py-2 text-sm text-gold-ink"
    >
      <CircleAlert aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
      <span>Evento em confirmação — entre em contato com a produção</span>
    </div>
  );
}
