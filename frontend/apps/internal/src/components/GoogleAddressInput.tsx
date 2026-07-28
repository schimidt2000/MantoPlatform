import { useMemo, useState } from "react";
import { Combobox, type ComboboxOption } from "@manto/ui";
import { MapPin } from "lucide-react";
import { ADDRESS_MIN_CHARS, useAddressAutocomplete } from "../lib/maps";

export interface GoogleAddressInputProps {
  /** Endereço atual (texto livre — o valor persistido é sempre a string). */
  value: string;
  onChange: (value: string) => void;
  /** Disparado só quando o usuário escolhe uma sugestão do Google (endereço normalizado). */
  onSelectSuggestion?: (description: string) => void;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
  id?: string;
  "aria-label"?: string;
  className?: string;
}

/**
 * Campo de endereço com preenchimento preditivo do Google Places (feature 195, Princípio X.3).
 *
 * Obrigatório em todo input de local/endereço do sistema — evita erro de logística e cálculo de
 * distância impreciso. É texto livre (`freeSolo`): o usuário pode digitar um endereço que o Google
 * não conhece, mas escolher uma sugestão grava a versão normalizada. As sugestões vêm do proxy
 * `/api/maps/address-autocomplete`, então a API Key nunca é exposta ao navegador.
 */
export function GoogleAddressInput({
  value,
  onChange,
  onSelectSuggestion,
  placeholder = "Rua, número, bairro, cidade…",
  disabled = false,
  invalid = false,
  id,
  "aria-label": ariaLabel,
  className,
}: GoogleAddressInputProps) {
  // Só o que o usuário digitar dispara busca — começa vazio para não gastar quota do Places
  // consultando um endereço já salvo toda vez que a tela de edição abre.
  const [query, setQuery] = useState("");
  const { suggestions, isLoading, isError } = useAddressAutocomplete(query);

  const options = useMemo<ComboboxOption[]>(
    () =>
      suggestions.map((s) => ({
        value: s.place_id || s.description,
        label: s.description,
        fallbackIcon: <MapPin className="h-4 w-4" aria-hidden="true" />,
      })),
    [suggestions],
  );

  const hint =
    query.trim().length < ADDRESS_MIN_CHARS
      ? `Digite ao menos ${ADDRESS_MIN_CHARS} letras para buscar no Google Maps.`
      : isError
        ? "Não foi possível buscar endereços agora — você pode digitar manualmente."
        : "Nenhum endereço encontrado — você pode digitar manualmente.";

  return (
    <Combobox
      freeSolo
      id={id}
      aria-label={ariaLabel}
      className={className}
      value={value}
      options={options}
      loading={isLoading}
      disabled={disabled}
      invalid={invalid}
      placeholder={placeholder}
      hintMessage={hint}
      emptyMessage={hint}
      onQueryChange={setQuery}
      onChange={(next, option) => {
        const text = next ?? "";
        onChange(text);
        setQuery(text);
        if (option) onSelectSuggestion?.(text);
      }}
    />
  );
}
