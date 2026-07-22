import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import { z } from "zod";

/** Mesmas opções do formulário Jinja (`app/templates/cadastro/form.html`) — fonte única. */
export const GENDER_OPTIONS = [
  "Homem Cis",
  "Mulher Cis",
  "Homem Trans",
  "Mulher Trans",
  "Não-Binário",
  "Prefiro não responder",
];

export const HOW_FOUND_US_OPTIONS = [
  "Instagram @mantoproducoes",
  "Instagram @castingmantoproducoes",
  "Indicação",
  "Site",
  "Anúncio",
  "Outros",
];

export const LANGUAGE_OPTIONS = [
  "Português",
  "Inglês",
  "Espanhol",
  "Francês",
  "Alemão",
  "Japonês",
  "Mandarim",
  "Hindi",
  "Árabe",
  "Libras",
];

export const RACE_OPTIONS = ["Branca", "Preta", "Parda", "Amarela", "Indígena"];

export const PIX_TYPE_OPTIONS = ["CPF", "CNPJ", "Telefone", "Chave aleatória", "e-mail"];

export const CLOTHING_SIZE_OPTIONS = ["XGG", "GG", "G", "M", "P", "PP"];

export const PASSPORT_OPTIONS = ["Apenas Passaporte", "Possuo Passaporte e Visto", "Não"];

export const SKILL_OPTIONS = [
  "Acrobacia",
  "Animação de Pista",
  "Apresentação de shows",
  "Atuação",
  "Canto",
  "Canto lírico",
  "Contorcionismo",
  "Coordenação de Eventos",
  "Dança",
  "DJ",
  "Dublagem",
  "Filmmaking",
  "Fotografia",
  "Instrumentos de Corda",
  "Instrumento de Percussão",
  "Instrumento de Sopro",
  "Malabarismo",
  "Manipulador de Bonecos",
  "Maquiagem Artística",
  "Maquiagem Artística com Prótese",
  "Maquiagem Social",
  "Mestre de Cerimônia",
  "Patinação",
  "Pirofagia",
  "Recreação",
  "Técnico de Som",
  "Transporte de Pessoas",
  "Transporte de Materiais",
];

export const DDI_OPTIONS: { code: string; label: string }[] = [
  { code: "+55", label: "🇧🇷 Brasil +55" },
  { code: "+1", label: "🇺🇸 EUA/Canadá +1" },
  { code: "+351", label: "🇵🇹 Portugal +351" },
  { code: "+54", label: "🇦🇷 Argentina +54" },
  { code: "+598", label: "🇺🇾 Uruguai +598" },
  { code: "+595", label: "🇵🇾 Paraguai +595" },
  { code: "+56", label: "🇨🇱 Chile +56" },
  { code: "+57", label: "🇨🇴 Colômbia +57" },
  { code: "+52", label: "🇲🇽 México +52" },
  { code: "+44", label: "🇬🇧 Reino Unido +44" },
  { code: "+34", label: "🇪🇸 Espanha +34" },
  { code: "+33", label: "🇫🇷 França +33" },
  { code: "+49", label: "🇩🇪 Alemanha +49" },
  { code: "+39", label: "🇮🇹 Itália +39" },
  { code: "+81", label: "🇯🇵 Japão +81" },
  { code: "+86", label: "🇨🇳 China +86" },
  { code: "+61", label: "🇦🇺 Austrália +61" },
];

/** Tamanho máximo de fotos/documentos, em bytes — mesmos limites do backend (`cadastro_ops.py`). */
export const PHOTO_MAX_BYTES = 8 * 1024 * 1024;
export const DOC_MAX_BYTES = 10 * 1024 * 1024;
export const PHOTO_ACCEPT = "image/jpeg,image/png,image/webp";
export const DOC_ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";

/**
 * Schema de validação client-side — espelha as obrigatoriedades do backend
 * (`app/cadastro/cadastro_ops.py:process_submission`, `contracts/cadastro-endpoints.md`).
 * Arquivos ficam fora do schema (geridos como estado separado — ver `CadastroFiles`).
 */
export const cadastroSchema = z
  .object({
    website: z.string(), // honeypot — sempre vazio para humanos
    worked_before: z.string(),
    how_found_us: z.string(),
    full_name: z.string().min(1, "Informe o nome completo."),
    artistic_name: z.string(),
    gender: z.string().min(1, "Selecione o gênero."),
    gender_other: z.string(),
    phone_ddi: z.string(),
    phone_national: z.string().min(1, "Informe um telefone com DDD."),
    email: z.string().min(1, "Informe um e-mail.").email("Informe um e-mail válido."),
    languages: z.array(z.string()).min(1, "Selecione ao menos um idioma."),
    birth_date: z.string().min(1, "Informe a data de nascimento."),
    is_foreigner: z.boolean(),
    cpf: z.string(),
    rg: z.string().min(1, "Informe o RG/documento."),
    pix_key_type: z.string().min(1, "Selecione o tipo de chave PIX."),
    pix_key: z.string().min(1, "Informe a chave PIX."),
    pix_key_secondary: z.string(),
    race: z.string().min(1, "Selecione a raça/cor."),
    height: z.string().min(1, "Informe a altura."),
    clothing_top: z.string().min(1, "Selecione o manequim superior."),
    clothing_bottom: z.string().min(1, "Selecione o manequim inferior."),
    shoe_size: z.string().min(1, "Informe o tamanho do sapato."),
    passport: z.string().min(1, "Responda sobre passaporte e visto."),
    skills: z.array(z.string()).min(1, "Selecione ao menos uma habilidade."),
    car_brand: z.string(),
    car_model: z.string(),
    car_year: z.string(),
    car_plate: z.string(),
    cnh_expiration: z.string(),
  })
  .refine((v) => v.is_foreigner || v.cpf.replace(/\D/g, "").length === 11, {
    message: "CPF inválido — confira os 11 dígitos.",
    path: ["cpf"],
  })
  .refine((v) => v.gender !== "Outro" || v.gender_other.trim().length > 0, {
    message: "Especifique o gênero.",
    path: ["gender_other"],
  });

export type CadastroFormValues = z.infer<typeof cadastroSchema>;

export const CADASTRO_DEFAULT_VALUES: CadastroFormValues = {
  website: "",
  worked_before: "",
  how_found_us: "",
  full_name: "",
  artistic_name: "",
  gender: "",
  gender_other: "",
  phone_ddi: "+55",
  phone_national: "",
  email: "",
  languages: [],
  birth_date: "",
  is_foreigner: false,
  cpf: "",
  rg: "",
  pix_key_type: "",
  pix_key: "",
  pix_key_secondary: "",
  race: "",
  height: "",
  clothing_top: "",
  clothing_bottom: "",
  shoe_size: "",
  passport: "",
  skills: [],
  car_brand: "",
  car_model: "",
  car_year: "",
  car_plate: "",
  cnh_expiration: "",
};

/** Arquivos do formulário — rosto/corpo/documento obrigatórios, CNH opcional. */
export interface CadastroFiles {
  photo_face: File | null;
  photo_full: File | null;
  doc_photo: File | null;
  cnh_file: File | null;
}

export interface CadastroSubmitResult {
  id: number | null;
}

function appendFormData(formData: FormData, values: CadastroFormValues, files: CadastroFiles) {
  for (const [key, value] of Object.entries(values)) {
    if (Array.isArray(value)) {
      for (const item of value) formData.append(key, item);
    } else if (typeof value === "boolean") {
      if (value) formData.append(key, "1");
    } else {
      formData.append(key, value);
    }
  }
  if (files.photo_face) formData.append("photo_face", files.photo_face);
  if (files.photo_full) formData.append("photo_full", files.photo_full);
  if (files.doc_photo) formData.append("doc_photo", files.doc_photo);
  if (files.cnh_file) formData.append("cnh_file", files.cnh_file);
}

/** Envia o cadastro público (multipart) — `contracts/cadastro-endpoints.md`. */
export function useSubmitCadastro() {
  return useMutation<CadastroSubmitResult, Error, { values: CadastroFormValues; files: CadastroFiles }>({
    mutationFn: ({ values, files }) => {
      const formData = new FormData();
      appendFormData(formData, values, files);
      return apiFetch<CadastroSubmitResult>("/api/cadastro", { method: "POST", body: formData });
    },
  });
}

/** Checagem de CPF em tempo real — só dispara com os 11 dígitos completos. */
export function useCheckCpf(cpf: string) {
  const digits = cpf.replace(/\D/g, "");
  return useQuery<{ exists: boolean; valid: boolean }>({
    queryKey: ["cadastro-check-cpf", digits],
    queryFn: () => apiFetch(`/api/cadastro/check-cpf?cpf=${digits}`),
    enabled: digits.length === 11,
    staleTime: 30_000,
  });
}
