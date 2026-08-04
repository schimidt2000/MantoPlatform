import { useState } from "react";
import {
  GoogleAddressInput as BaseGoogleAddressInput,
  type GoogleAddressInputProps as BaseProps,
} from "@manto/ui";
import {
  ADDRESS_ENDPOINT_INTERNAL,
  ADDRESS_MIN_CHARS,
  useAddressAutocomplete,
} from "@manto/api-client";

export type GoogleAddressInputProps = Omit<
  BaseProps,
  "autocomplete" | "onQueryChange" | "minChars"
>;

/**
 * Campo de endereço do app interno — liga o componente de `@manto/ui` ao endpoint autenticado.
 *
 * O componente e a busca vivem nos pacotes compartilhados desde a feature 205 (`@manto/ui` e
 * `@manto/api-client`); o que sobra aqui é só a escolha do endpoint. O checkout público tem um
 * arquivo espelho apontando para a variante sem login — mesma implementação, gates diferentes.
 */
export function GoogleAddressInput(props: GoogleAddressInputProps) {
  const [query, setQuery] = useState("");
  const autocomplete = useAddressAutocomplete(query, ADDRESS_ENDPOINT_INTERNAL);

  return (
    <BaseGoogleAddressInput
      {...props}
      autocomplete={autocomplete}
      onQueryChange={setQuery}
      minChars={ADDRESS_MIN_CHARS}
    />
  );
}
