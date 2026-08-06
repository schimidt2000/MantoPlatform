import { useMemo } from "react";
import { Combobox, type ComboboxOption } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { useFigurinoSheets } from "../../lib/figurino";

/** Remove acentos e caixa — mesmo espírito do `strip_accents_lower` do backend. */
function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

export interface FigurinoPickerProps {
  value: number | null;
  onChange: (sheetId: number | null) => void;
  /**
   * Nome do personagem do cargo: as fichas cujo nome bate sobem para o topo da lista — mesmo
   * match por nome normalizado que a impressão de fichas usa.
   */
  characterName?: string;
  disabled?: boolean;
  ariaLabel: string;
  className?: string;
}

/**
 * Busca visual de ficha de figurino (feature 215).
 *
 * Substitui o `<datalist>` do card de figurino, que no Chrome não renderiza imagem nenhuma e
 * só vinculava a ficha no `blur` do campo — digitar errado significava não vincular nada, sem
 * aviso. Aqui é o `Combobox` do design system com a miniatura quadrada da ficha (Princípio
 * X.2), filtro em tempo real e vínculo no clique.
 */
export function FigurinoPicker({
  value,
  onChange,
  characterName,
  disabled = false,
  ariaLabel,
  className,
}: FigurinoPickerProps) {
  const query = useFigurinoSheets();
  const items = query.data?.items;

  const options = useMemo<ComboboxOption[]>(() => {
    const sheets = items ?? [];
    const charNorm = normalize((characterName ?? "").trim());
    // Sugestão primeiro: a ficha homônima do personagem é o caso esmagadoramente comum.
    const ordered = charNorm
      ? [...sheets].sort((a, b) => {
          const aHit = normalize(a.character_name).includes(charNorm) ? 0 : 1;
          const bHit = normalize(b.character_name).includes(charNorm) ? 0 : 1;
          return aHit !== bHit ? aHit - bHit : 0;
        })
      : sheets;
    return ordered.map((sheet) => ({
      value: String(sheet.id),
      label: sheet.character_name,
      imageUrl: sheet.photo_url ? assetUrl(sheet.photo_url) : null,
      imageShape: "square" as const,
      fallbackIcon: "👗",
    }));
  }, [items, characterName]);

  return (
    <Combobox
      className={className}
      aria-label={ariaLabel}
      placeholder="🔍 Buscar ficha de figurino…"
      emptyMessage="Nenhuma ficha encontrada."
      options={options}
      loading={query.isLoading}
      disabled={disabled}
      value={value != null ? String(value) : null}
      onChange={(next) => onChange(next ? Number(next) : null)}
    />
  );
}
