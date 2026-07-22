import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export type FormType = "comum" | "corporativo";

export type FieldType =
  | "texto_curto"
  | "texto_longo"
  | "selecao"
  | "data"
  | "hora"
  | "telefone"
  | "email"
  | "cpf"
  | "cnpj"
  | "cep"
  | "sim_nao";

export interface FieldSchema {
  key: string;
  type: FieldType;
  label: string;
  help_text: string | null;
  placeholder: string | null;
  required: boolean;
  options: string[] | null;
}

export interface SectionSchema {
  secao: string;
  campos: FieldSchema[];
}

export interface FormSchema {
  title: string;
  header: string;
  sections: SectionSchema[];
}

export interface FormSubmitResult {
  wa_link: string | null;
  contact_name: string | null;
}

/** Estrutura vigente de um dos dois formulários públicos — muda sem deploy (feature 123). */
export function useFormSchema(formType: FormType) {
  return useQuery<FormSchema>({
    queryKey: ["formularios-schema", formType],
    queryFn: () => apiFetch<FormSchema>(`/api/formularios/${formType}/schema`),
  });
}

/** Envia a submissão (multipart) — `contracts/formularios-endpoints.md`. */
export function useSubmitForm(formType: FormType) {
  return useMutation<FormSubmitResult, Error, FormData>({
    mutationFn: (formData) =>
      apiFetch<FormSubmitResult>(`/api/formularios/${formType}`, {
        method: "POST",
        body: formData,
      }),
  });
}

/** Mesmos DDIs oferecidos pelo formulário Jinja (`_field_macros.html:phone_field`). */
export const DDI_OPTIONS: { code: string; flag: string }[] = [
  { code: "+55", flag: "🇧🇷" },
  { code: "+1", flag: "🇺🇸" },
  { code: "+351", flag: "🇵🇹" },
  { code: "+34", flag: "🇪🇸" },
  { code: "+44", flag: "🇬🇧" },
  { code: "+33", flag: "🇫🇷" },
  { code: "+49", flag: "🇩🇪" },
  { code: "+39", flag: "🇮🇹" },
  { code: "+54", flag: "🇦🇷" },
  { code: "+598", flag: "🇺🇾" },
];

/** Mesmas máscaras leves de digitação de `_form_scripts.html` — formatam, não validam. */
export function maskCpf(digitsOnly: string): string {
  const d = digitsOnly.slice(0, 11);
  return d
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}

export function maskCnpj(digitsOnly: string): string {
  const d = digitsOnly.slice(0, 14);
  return d
    .replace(/(\d{2})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1/$2")
    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

export function maskCep(digitsOnly: string): string {
  const d = digitsOnly.slice(0, 8);
  return d.replace(/(\d{5})(\d{1,3})$/, "$1-$2");
}

export function maskPhone(digitsOnly: string): string {
  const d = digitsOnly.slice(0, 11);
  if (d.length > 10) return d.replace(/(\d{2})(\d{5})(\d{1,4})/, "($1) $2-$3");
  if (d.length > 6) return d.replace(/(\d{2})(\d{4})(\d{1,4})/, "($1) $2-$3");
  if (d.length > 2) return d.replace(/(\d{2})(\d+)/, "($1) $2");
  return d;
}

export function onlyDigits(value: string): string {
  return value.replace(/\D/g, "");
}

/** Campos de endereço acoplados ao autopreenchimento por CEP (`research.md` §4). */
export const CEP_TARGET_KEYS = ["logradouro", "bairro", "cidade", "estado"] as const;

interface ViaCepResponse {
  erro?: boolean;
  logradouro?: string;
  bairro?: string;
  localidade?: string;
  uf?: string;
}

/** Consulta o ViaCEP direto do navegador — falha silenciosa (nunca bloqueia o envio). */
export async function fetchCep(cep: string): Promise<Partial<Record<string, string>> | null> {
  try {
    const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
    const data = (await response.json()) as ViaCepResponse;
    if (data.erro) return null;
    return {
      logradouro: data.logradouro,
      bairro: data.bairro,
      cidade: data.localidade,
      estado: data.uf,
    };
  } catch {
    return null;
  }
}
