import { cn } from "@manto/ui";

export type StatusValue = "em_revisao" | "aprovado" | "precisa_ajustes" | "rejeitado";

export const STATUS_META: Record<StatusValue, { label: string; text: string; bg: string }> = {
  em_revisao: { label: "Em Revisão", text: "text-blue", bg: "bg-blue-soft" },
  aprovado: { label: "Aprovado", text: "text-green", bg: "bg-green-soft" },
  precisa_ajustes: { label: "Precisa de Ajustes", text: "text-gold", bg: "bg-gold-soft" },
  rejeitado: { label: "Rejeitado", text: "text-red", bg: "bg-red-soft" },
};

const STATUS_ORDER: StatusValue[] = ["em_revisao", "aprovado", "precisa_ajustes", "rejeitado"];

export interface StatusBadgeProps {
  status: StatusValue;
  /** Só quem gerencia o espaço (`review_ops.can_manage`) vê os botões de troca de status. */
  canManage: boolean;
  onChange: (status: StatusValue) => void;
  isPending: boolean;
}

/** Badge de status de aprovação + ações de um clique para quem gerencia o espaço (feature 182). */
export function StatusBadge({ status, canManage, onChange, isPending }: StatusBadgeProps) {
  const meta = STATUS_META[status];
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={cn("rounded-full px-3 py-1 text-xs font-semibold", meta.bg, meta.text)}>
        {meta.label}
      </span>
      {canManage && (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Alterar status de aprovação">
          {STATUS_ORDER.filter((value) => value !== status).map((value) => (
            <button
              key={value}
              type="button"
              disabled={isPending}
              onClick={() => onChange(value)}
              className={cn(
                "rounded-full border border-line px-2.5 py-1 text-xs font-medium text-muted transition-colors hover:border-transparent hover:text-white disabled:pointer-events-none disabled:opacity-60",
                value === "aprovado" && "hover:bg-green",
                value === "precisa_ajustes" && "hover:bg-gold",
                value === "rejeitado" && "hover:bg-red",
                value === "em_revisao" && "hover:bg-blue",
              )}
            >
              {STATUS_META[value].label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
