import { useMemo, useState } from "react";
import { MapPin } from "lucide-react";
import { Combobox, type ComboboxOption } from "./combobox";

/** Sugestão devolvida pelo proxy de autocomplete do backend. */
export interface AddressSuggestionLike {
  description: string;
  place_id: string;
}

/** O que o componente precisa saber sobre a busca — injetado por quem o usa. */
export interface AddressAutocompleteState {
  suggestions: AddressSuggestionLike[];
  isLoading: boolean;
  isError: boolean;
}

export interface GoogleAddressInputProps {
  /** Endereço atual (texto livre — o valor persistido é sempre a string). */
  value: string;
  onChange: (value: string) => void;
  /** Disparado só quando o usuário escolhe uma sugestão do Google (endereço normalizado). */
  onSelectSuggestion?: (description: string) => void;
  /**
   * Resultado do hook de busca. Vem por prop, e não de um `useQuery` interno, porque
   * `@manto/ui` é puramente apresentacional — quem busca é `@manto/api-client`
   * (`useAddressAutocomplete`), e o endpoint muda entre o app interno e o checkout público.
   */
  autocomplete: AddressAutocompleteState;
  /** Chamado a cada tecla; alimenta o hook de busca de quem usa o componente. */
  onQueryChange: (query: string) => void;
  /** Mínimo de caracteres antes de buscar — só para compor a mensagem de dica. */
  minChars?: number;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
  id?: string;
  "aria-label"?: string;
  className?: string;
}

/**
 * Campo de endereço com preenchimento preditivo do Google Places (feature 195, Princípio XII.3).
 *
 * Obrigatório em **todo** input de endereço do sistema — evita erro de logística e cálculo de
 * distância impreciso. É texto livre (`freeSolo`): o usuário pode digitar um endereço que o Google
 * não conhece, mas escolher uma sugestão grava a versão normalizada.
 *
 * Promovido de `apps/internal` para cá na feature 205, quando o checkout público passou a precisar
 * do mesmo campo. Copiar teria criado duas fontes de verdade para a regra de endereço — o que o
 * Princípio I proíbe.
 */
function GoogleAddressInput({
  value,
  onChange,
  onSelectSuggestion,
  autocomplete,
  onQueryChange,
  minChars = 3,
  placeholder = "Rua, número, bairro, cidade…",
  disabled = false,
  invalid = false,
  id,
  "aria-label": ariaLabel,
  className,
}: GoogleAddressInputProps) {
  // Só o que o usuário digitar dispara busca — começa vazio para não gastar quota do Places
  // consultando um endereço já salvo toda vez que a tela abre.
  const [query, setQuery] = useState("");

  const options = useMemo<ComboboxOption[]>(
    () =>
      autocomplete.suggestions.map((s) => ({
        value: s.place_id || s.description,
        label: s.description,
        fallbackIcon: <MapPin className="h-4 w-4" aria-hidden="true" />,
      })),
    [autocomplete.suggestions],
  );

  const hint =
    query.trim().length < minChars
      ? `Digite ao menos ${minChars} letras para buscar no Google Maps.`
      : autocomplete.isError
        ? "Não foi possível buscar endereços agora — você pode digitar manualmente."
        : "Nenhum endereço encontrado — você pode digitar manualmente.";

  const handleQuery = (next: string) => {
    setQuery(next);
    onQueryChange(next);
  };

  return (
    <Combobox
      freeSolo
      id={id}
      aria-label={ariaLabel}
      className={className}
      value={value}
      options={options}
      loading={autocomplete.isLoading}
      disabled={disabled}
      invalid={invalid}
      placeholder={placeholder}
      hintMessage={hint}
      emptyMessage={hint}
      onQueryChange={handleQuery}
      onChange={(next, option) => {
        const text = next ?? "";
        onChange(text);
        handleQuery(text);
        if (option) onSelectSuggestion?.(text);
      }}
    />
  );
}

export { GoogleAddressInput };
