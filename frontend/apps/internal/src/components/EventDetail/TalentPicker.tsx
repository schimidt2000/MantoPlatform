import { useMemo } from "react";
import { Badge, Combobox, type ComboboxOption } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { useCastingOptions, type TalentoEscalavel } from "../../lib/casting";

/**
 * Selo de agenda de uma opção da busca (feature 215).
 *
 * O aviso de choque existia só DEPOIS de escalar, no card do cargo — quem estava escolhendo
 * não via nada e só descobria o conflito ao salvar. Aqui ele aparece na própria lista, com a
 * mesma escala de cor do card: vermelho para sobreposição de horário, dourado para outro
 * compromisso no mesmo dia.
 */
function OcupadoBadge({ talent }: { talent: TalentoEscalavel }) {
  const status = talent.availability?.status;
  if (!status || status === "free") return null;
  const isConflict = status === "conflict";
  return (
    <Badge tone={isConflict ? "red" : "gold"}>
      {isConflict ? "● Ocupado" : "● Mesmo dia"}
    </Badge>
  );
}

export interface TalentPickerProps {
  /** Evento aberto — a disponibilidade é calculada contra a janela dele. */
  eventId: number;
  value: number | null;
  onChange: (talentId: number | null) => void;
  disabled?: boolean;
  ariaLabel: string;
  className?: string;
}

/**
 * Busca visual de talento para escalar (feature 215).
 *
 * Substitui o `<select>` nativo do card de casting, que listava centenas de nomes sem foto e
 * sem indicar quem já estava comprometido. Usa o `Combobox` do design system (Princípio X.1:
 * lista com mais de 10 itens é busca, não `<select>`) com o avatar circular de pessoa e o selo
 * de agenda — filtro em tempo real, ignorando acentos, sem ida ao servidor a cada tecla.
 */
export function TalentPicker({
  eventId,
  value,
  onChange,
  disabled = false,
  ariaLabel,
  className,
}: TalentPickerProps) {
  const query = useCastingOptions(eventId);
  const items = query.data?.items;

  const options = useMemo<ComboboxOption[]>(
    () =>
      (items ?? []).map((talent) => ({
        value: String(talent.id),
        label: talent.name,
        description: talent.availability?.info || talent.artistic_name || null,
        imageUrl: talent.photo_url ? assetUrl(talent.photo_url, { largura: 128 }) : null,
        imageShape: "circle" as const,
        badge: <OcupadoBadge talent={talent} />,
      })),
    [items],
  );

  return (
    <Combobox
      className={className}
      aria-label={ariaLabel}
      placeholder="🔍 Buscar talento…"
      emptyMessage="Nenhum talento encontrado."
      options={options}
      loading={query.isLoading}
      disabled={disabled}
      value={value != null ? String(value) : null}
      onChange={(next) => onChange(next ? Number(next) : null)}
    />
  );
}
