import { useMemo } from "react";
import { Combobox, type ComboboxOption } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { useFigurinoSheets } from "../lib/figurino";

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
   * Nome do personagem: as fichas cujo nome bate sobem para o topo da lista — mesmo
   * match por nome normalizado que a impressão de fichas usa.
   */
  characterName?: string;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
  placeholder?: string;
}

/**
 * Busca visual de ficha de figurino — **a única porta para escolher uma ficha** no app.
 *
 * Nasceu na feature 215 para substituir o `<datalist>` do card de figurino (que no Chrome não
 * renderiza imagem nenhuma e só vinculava no `blur`: digitar errado significava não vincular
 * nada, sem aviso). Em 225d absorveu o `FigurinoSheetPicker` da 209, que resolvia o mesmo
 * problema com uma lista própria — duas buscas de ficha com aparências diferentes era
 * exatamente o que o Princípio de consistência proíbe, e a do design system ganha porque o
 * `Combobox` já traz filtro sem acento, teto de resultados, limpar e navegação por teclado.
 *
 * São 616 fichas: escolher por nome numa lista alfabética é inviável, e a escolha é visual por
 * natureza — daí a miniatura quadrada em cada resultado (Princípio X.2).
 */
export function FigurinoPicker({
  value,
  onChange,
  characterName,
  disabled = false,
  ariaLabel,
  className,
  placeholder,
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
      aria-label={ariaLabel ?? "Buscar ficha de figurino"}
      placeholder={placeholder ?? "🔍 Buscar ficha de figurino…"}
      emptyMessage="Nenhuma ficha encontrada."
      options={options}
      loading={query.isLoading}
      disabled={disabled}
      value={value != null ? String(value) : null}
      onChange={(next) => onChange(next ? Number(next) : null)}
    />
  );
}
