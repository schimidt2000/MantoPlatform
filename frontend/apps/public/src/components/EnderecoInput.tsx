import { useState } from "react";
import {
  GoogleAddressInput as BaseGoogleAddressInput,
  type GoogleAddressInputProps as BaseProps,
} from "@manto/ui";
import {
  ADDRESS_ENDPOINT_PUBLIC,
  ADDRESS_MIN_CHARS,
  useAddressAutocomplete,
} from "@manto/api-client";

export type EnderecoInputProps = Omit<BaseProps, "autocomplete" | "onQueryChange" | "minChars">;

/**
 * Campo de endereço do checkout público — liga o componente de `@manto/ui` ao endpoint **sem
 * login** (feature 205).
 *
 * Espelho do binding do app interno: mesma implementação de campo e de busca, endpoint diferente.
 * O do staff exige sessão; este é anônimo por natureza e tem teto por origem no servidor. A chave
 * do Google continua só no backend nos dois casos (Princípio XII.4).
 */
export function EnderecoInput(props: EnderecoInputProps) {
  const [query, setQuery] = useState("");
  const autocomplete = useAddressAutocomplete(query, ADDRESS_ENDPOINT_PUBLIC);

  return (
    <BaseGoogleAddressInput
      {...props}
      autocomplete={autocomplete}
      onQueryChange={setQuery}
      minChars={ADDRESS_MIN_CHARS}
    />
  );
}
