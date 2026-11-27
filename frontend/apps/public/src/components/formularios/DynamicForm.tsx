import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, CardHeader, CardTitle, CardContent, Skeleton } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { MENSAGEM_DOC_INVALIDO, docValido } from "../../lib/documento";
import { codigoDoSite } from "../../lib/origem";
import {
  CEP_TARGET_KEYS,
  CHAVE_DOC_DA_NOTA,
  CHAVE_EMAIL_DA_NOTA,
  CHAVE_PRECISA_NOTA,
  RESPOSTA_DA_VERSAO,
  campoVisivel,
  fetchCep,
  onlyDigits,
  useFormSchema,
  useSubmitForm,
  type FieldSchema,
  type FormType,
  type VersaoDaNota,
} from "../../lib/formularios";
import { DynamicField } from "./DynamicField";

interface DynamicFormProps {
  formType: FormType;
  /** Hotfix 342b: com versão, a resposta da nota é fixa e a caixa "Preciso de nota fiscal" some. */
  versao?: VersaoDaNota;
}

/** O documento e o e-mail digitados no começo do formulário, que adiantam as respostas da nota. */
function docDeOrigem(values: Record<string, string>): string {
  return values.cnpj || values.cpf || "";
}

function flattenFields(sections: { campos: FieldSchema[] }[]): FieldSchema[] {
  return sections.flatMap((section) => section.campos);
}

function buildFormData(
  fields: FieldSchema[],
  values: Record<string, string>,
  versao: VersaoDaNota | undefined,
): FormData {
  const formData = new FormData();
  formData.append("website", values.website ?? ""); // honeypot — sempre vazio para humanos
  // Hotfix 342b: o servidor fixa "Preciso de nota fiscal" pela versão do link, não pela caixa.
  if (versao) formData.append("versao_nota", versao);
  for (const field of fields) {
    // Feature 342: o que ficou digitado num campo escondido não segue (o servidor também descarta).
    if (!campoVisivel(field, values)) continue;
    if (field.type === "telefone") {
      formData.append(`${field.key}_ddi`, values[`${field.key}_ddi`] ?? "+55");
      formData.append(`${field.key}_national`, values[`${field.key}_national`] ?? "");
    } else if (field.type === "sim_nao") {
      if (values[field.key] === "Sim") formData.append(field.key, "Sim");
    } else {
      formData.append(field.key, values[field.key] ?? "");
    }
  }
  // Feature 348: o código do clique de campanha; o servidor põe a linha no fim da mensagem do WhatsApp.
  const codigo = codigoDoSite();
  if (codigo) formData.append("origem_codigo", codigo);
  return formData;
}

export function DynamicForm({ formType, versao }: DynamicFormProps) {
  const navigate = useNavigate();
  const schema = useFormSchema(formType);
  const submitForm = useSubmitForm(formType);
  const [values, setValues] = useState<Record<string, string>>(() => {
    const iniciais: Record<string, string> = {};
    if (versao) iniciais[CHAVE_PRECISA_NOTA] = RESPOSTA_DA_VERSAO[versao];
    return iniciais;
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);

  const setValue = (key: string, value: string) => {
    setValues((prev) => {
      const next = { ...prev, [key]: value };
      // Feature 342: ao marcar "Preciso de nota fiscal", o documento e o e-mail já digitados acima
      // adiantam as respostas da nota. Só em campo vazio: nunca troca o que a cliente escreveu.
      if (key === CHAVE_PRECISA_NOTA && value === "Sim") {
        if (!prev[CHAVE_DOC_DA_NOTA]) next[CHAVE_DOC_DA_NOTA] = docDeOrigem(prev);
        if (!prev[CHAVE_EMAIL_DA_NOTA]) next[CHAVE_EMAIL_DA_NOTA] = prev.email || "";
      }
      // Hotfix 342b: no link com nota as perguntas já estão abertas antes do documento e do e-mail
      // serem digitados; elas acompanham o que a cliente escreve acima enquanto ela não as mudar.
      if (next[CHAVE_PRECISA_NOTA] === "Sim" && key !== CHAVE_PRECISA_NOTA) {
        if (
          (key === "cpf" || key === "cnpj") &&
          (prev[CHAVE_DOC_DA_NOTA] ?? "") === docDeOrigem(prev)
        ) {
          next[CHAVE_DOC_DA_NOTA] = docDeOrigem(next);
        }
        if (key === "email" && (prev[CHAVE_EMAIL_DA_NOTA] ?? "") === (prev.email ?? "")) {
          next[CHAVE_EMAIL_DA_NOTA] = value;
        }
      }
      return next;
    });
    setErrors((prev) => (prev[key] ? { ...prev, [key]: "" } : prev));
  };

  /** Avisa do documento errado ao sair do campo, sem esperar o envio. */
  const conferirDoc = (key: string, value: string) => {
    if (value.trim() && !docValido(value)) {
      setErrors((prev) => ({ ...prev, [key]: MENSAGEM_DOC_INVALIDO }));
    }
  };

  async function handleBlurCep(rawValue: string) {
    const digits = onlyDigits(rawValue);
    if (digits.length !== 8 || !schema.data) return;
    const fields = flattenFields(schema.data.sections);
    const fieldKeys = new Set(fields.map((f) => f.key));
    const result = await fetchCep(digits);
    if (!result) return;
    setValues((prev) => {
      const next = { ...prev };
      for (const key of CEP_TARGET_KEYS) {
        if (fieldKeys.has(key) && !prev[key] && result[key]) next[key] = result[key] as string;
      }
      return next;
    });
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!schema.data) return;
    setServerError(null);
    const fields = flattenFields(schema.data.sections);
    const formData = buildFormData(fields, values, versao);

    submitForm.mutate(formData, {
      onSuccess: (result) => {
        navigate(`/f/${formType}/enviado`, { state: result });
      },
      onError: (error) => {
        if (error instanceof ApiRequestError && error.fields) {
          setErrors((prev) => ({ ...prev, ...error.fields }));
        }
        setServerError(error.message);
      },
    });
  }

  if (schema.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (schema.isError || !schema.data) {
    return (
      <div className="rounded-lg border border-red bg-red-soft p-4 text-sm text-red" role="alert">
        Não foi possível carregar o formulário. Tente novamente em instantes.
      </div>
    );
  }

  const paymentMethod = values.forma_pagamento;
  // O que aparece de cada seção. Com versão, a caixa da nota é fixa e não aparece; no link sem
  // nota a seção "Nota fiscal" fica vazia e some inteira.
  const camposVisiveis = (campos: FieldSchema[]) =>
    campos
      .filter((field) => field.key !== "descreva_outros" || paymentMethod === "Outros")
      .filter((field) => !(versao && field.key === CHAVE_PRECISA_NOTA))
      .filter((field) => campoVisivel(field, values));

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {/* Honeypot anti-bot: humanos nunca preenchem — fora do fluxo de tab e da leitura de tela. */}
      <div className="absolute -left-[9999px] top-[-9999px]" aria-hidden="true">
        <label>Não preencha este campo</label>
        <input
          type="text"
          tabIndex={-1}
          autoComplete="off"
          value={values.website ?? ""}
          onChange={(e) => setValue("website", e.target.value)}
        />
      </div>

      {serverError && (
        <div className="rounded-lg border border-red bg-red-soft p-3 text-sm text-red" role="alert">
          ⚠️ {serverError}
        </div>
      )}

      {schema.data.sections
        .filter((section) => camposVisiveis(section.campos).length > 0)
        .map((section) => (
          <Card key={section.secao}>
            <CardHeader>
              <CardTitle>{section.secao}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {camposVisiveis(section.campos).map((field) => (
                <DynamicField
                  key={field.key}
                  field={field}
                  values={values}
                  errors={errors}
                  onChange={setValue}
                  onBlurCep={field.type === "cep" ? handleBlurCep : undefined}
                  onBlurDoc={conferirDoc}
                />
              ))}
            </CardContent>
          </Card>
        ))}

      <Button type="submit" size="lg" className="w-full" loading={submitForm.isPending}>
        {submitForm.isPending ? "Enviando…" : "Enviar no WhatsApp"}
      </Button>
    </form>
  );
}
