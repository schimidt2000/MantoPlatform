import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, CardHeader, CardTitle, CardContent, Skeleton } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { MENSAGEM_DOC_INVALIDO, docValido } from "../../lib/documento";
import {
  CEP_TARGET_KEYS,
  CHAVE_DOC_DA_NOTA,
  CHAVE_EMAIL_DA_NOTA,
  CHAVE_PRECISA_NOTA,
  campoVisivel,
  fetchCep,
  onlyDigits,
  useFormSchema,
  useSubmitForm,
  type FieldSchema,
  type FormType,
} from "../../lib/formularios";
import { DynamicField } from "./DynamicField";

interface DynamicFormProps {
  formType: FormType;
}

function flattenFields(sections: { campos: FieldSchema[] }[]): FieldSchema[] {
  return sections.flatMap((section) => section.campos);
}

function buildFormData(fields: FieldSchema[], values: Record<string, string>): FormData {
  const formData = new FormData();
  formData.append("website", values.website ?? ""); // honeypot — sempre vazio para humanos
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
  return formData;
}

export function DynamicForm({ formType }: DynamicFormProps) {
  const navigate = useNavigate();
  const schema = useFormSchema(formType);
  const submitForm = useSubmitForm(formType);
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);

  const setValue = (key: string, value: string) => {
    setValues((prev) => {
      const next = { ...prev, [key]: value };
      // Feature 342: ao marcar "Preciso de nota fiscal", o documento e o e-mail já digitados acima
      // adiantam as respostas da nota. Só em campo vazio: nunca troca o que a cliente escreveu.
      if (key === CHAVE_PRECISA_NOTA && value === "Sim") {
        if (!prev[CHAVE_DOC_DA_NOTA]) next[CHAVE_DOC_DA_NOTA] = prev.cnpj || prev.cpf || "";
        if (!prev[CHAVE_EMAIL_DA_NOTA]) next[CHAVE_EMAIL_DA_NOTA] = prev.email || "";
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
    const formData = buildFormData(fields, values);

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

      {schema.data.sections.map((section) => (
        <Card key={section.secao}>
          <CardHeader>
            <CardTitle>{section.secao}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {section.campos
              .filter((field) => field.key !== "descreva_outros" || paymentMethod === "Outros")
              .filter((field) => campoVisivel(field, values))
              .map((field) => (
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
