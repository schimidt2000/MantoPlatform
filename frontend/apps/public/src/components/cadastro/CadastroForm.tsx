import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, CardHeader, CardTitle, CardContent, FileUpload } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import {
  CADASTRO_DEFAULT_VALUES,
  cadastroSchema,
  DDI_OPTIONS,
  DOC_ACCEPT,
  DOC_MAX_BYTES,
  GENDER_OPTIONS,
  HOW_FOUND_US_OPTIONS,
  LANGUAGE_OPTIONS,
  PASSPORT_OPTIONS,
  PHOTO_ACCEPT,
  PHOTO_MAX_BYTES,
  PIX_TYPE_OPTIONS,
  CLOTHING_SIZE_OPTIONS,
  RACE_OPTIONS,
  SKILL_OPTIONS,
  suggestEmailCorrection,
  useSubmitCadastro,
  type CadastroFiles,
  type CadastroFormValues,
} from "../../lib/cadastro";
import { CpfField } from "./CpfField";

/** Mapeia o campo do erro 400 da API para o campo do formulário React (mesmos nomes hoje). */
const FILE_FIELDS = new Set(["photo_face", "photo_full", "doc_photo", "cnh_file"]);

const FIELD = "h-11 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink";
const LABEL = "mb-1 block text-sm text-muted";

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p className="mt-1 text-sm text-red" role="alert">
      {message}
    </p>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {hint && <p className="text-xs text-muted">{hint}</p>}
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

interface RadioGroupProps {
  label: string;
  name: keyof CadastroFormValues;
  options: string[];
  required?: boolean;
  register: ReturnType<typeof useForm<CadastroFormValues>>["register"];
  error?: string;
}

function RadioGroup({ label, name, options, required, register, error }: RadioGroupProps) {
  return (
    <div>
      <label className={LABEL}>
        {label} {required && <span className="text-red">*</span>}
      </label>
      <div className="flex flex-col gap-2">
        {options.map((option) => (
          <label key={option} className="flex items-center gap-2 text-sm text-ink">
            <input type="radio" value={option} className="h-[18px] w-[18px] accent-accent" {...register(name)} />
            {option}
          </label>
        ))}
      </div>
      <FieldError message={error} />
    </div>
  );
}

interface CheckboxGroupProps {
  label: string;
  name: "languages" | "skills";
  options: string[];
  required?: boolean;
  register: ReturnType<typeof useForm<CadastroFormValues>>["register"];
  error?: string;
}

function CheckboxGroup({ label, name, options, required, register, error }: CheckboxGroupProps) {
  return (
    <div>
      <label className={LABEL}>
        {label} {required && <span className="text-red">*</span>}
      </label>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {options.map((option) => (
          <label key={option} className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              value={option}
              className="h-[18px] w-[18px] accent-accent"
              {...register(name)}
            />
            {option}
          </label>
        ))}
      </div>
      <FieldError message={error} />
    </div>
  );
}

export function CadastroForm() {
  const navigate = useNavigate();
  const submitCadastro = useSubmitCadastro();
  const [serverError, setServerError] = useState<string | null>(null);
  const [files, setFiles] = useState<CadastroFiles>({
    photo_face: null,
    photo_full: null,
    doc_photo: null,
    cnh_file: null,
  });
  const [fileErrors, setFileErrors] = useState<Partial<Record<keyof CadastroFiles, string>>>({});

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<CadastroFormValues>({
    resolver: zodResolver(cadastroSchema),
    defaultValues: CADASTRO_DEFAULT_VALUES,
  });

  const gender = watch("gender");
  const isForeigner = watch("is_foreigner");
  const cpf = watch("cpf");
  const emailTypo = suggestEmailCorrection(watch("email"));

  function validateFiles(): boolean {
    const nextErrors: Partial<Record<keyof CadastroFiles, string>> = {};
    if (!files.photo_face) nextErrors.photo_face = "Anexe a foto do rosto.";
    if (!files.photo_full) nextErrors.photo_full = "Anexe a foto de corpo inteiro.";
    if (!files.doc_photo) nextErrors.doc_photo = "Anexe a foto do documento.";
    setFileErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  const onSubmit = handleSubmit((values) => {
    setServerError(null);
    if (!validateFiles()) return;

    submitCadastro.mutate(
      { values, files },
      {
        // O cadastro já está gravado aqui: `state` só carrega o que a tela de sucesso precisa
        // para oferecer a correção do email sem refazer nada (feature 219).
        onSuccess: (result) =>
          navigate("/cadastro/enviado", {
            state: { id: result.id, email: result.email, token: result.verify_token },
          }),
        onError: (error) => {
          if (error instanceof ApiRequestError && error.fields) {
            const messages: string[] = [];
            for (const [field, message] of Object.entries(error.fields)) {
              messages.push(message);
              if (FILE_FIELDS.has(field)) {
                setFileErrors((prev) => ({ ...prev, [field]: message }));
              } else {
                setError(field as keyof CadastroFormValues, { message });
              }
            }
            setServerError(messages.join(" "));
            return;
          }
          setServerError(error.message);
        },
      },
    );
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      {/* Honeypot anti-bot: humanos nunca preenchem — fora do fluxo de tab e da leitura de tela. */}
      <div className="absolute -left-[9999px] top-[-9999px]" aria-hidden="true">
        <label>Não preencha este campo</label>
        <input type="text" tabIndex={-1} autoComplete="off" {...register("website")} />
      </div>

      {serverError && (
        <div className="rounded-lg border border-red bg-red-soft p-3 text-sm text-red" role="alert">
          ⚠️ {serverError}
        </div>
      )}

      <Section title="✨ Sobre você">
        <RadioGroup
          label="Já trabalhou com a Manto? (opcional)"
          name="worked_before"
          options={["Sim", "Não"]}
          register={register}
        />
        <RadioGroup
          label="Onde conheceu a Manto? (opcional)"
          name="how_found_us"
          options={HOW_FOUND_US_OPTIONS}
          register={register}
        />
      </Section>

      <Section title="👤 Dados pessoais">
        <div>
          <label className={LABEL}>
            Nome completo <span className="text-red">*</span>
          </label>
          <input className={FIELD} {...register("full_name")} />
          <FieldError message={errors.full_name?.message} />
        </div>
        <div>
          <label className={LABEL}>Nome artístico (opcional)</label>
          <input className={FIELD} {...register("artistic_name")} />
        </div>
        <RadioGroup
          label="Gênero"
          name="gender"
          options={GENDER_OPTIONS}
          required
          register={register}
          error={errors.gender?.message}
        />
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="radio" value="Outro" className="h-[18px] w-[18px] accent-accent" {...register("gender")} />
          Outro:
        </label>
        {gender === "Outro" && (
          <div>
            <input className={FIELD} placeholder="Especifique" {...register("gender_other")} />
            <FieldError message={errors.gender_other?.message} />
          </div>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[auto_1fr]">
          <div>
            <label className={LABEL}>
              Telefone / WhatsApp <span className="text-red">*</span>
            </label>
            <div className="flex gap-2">
              <select className={`${FIELD} w-auto`} {...register("phone_ddi")}>
                {DDI_OPTIONS.map((opt) => (
                  <option key={opt.code} value={opt.code}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <input
                className={FIELD}
                inputMode="tel"
                placeholder="(11) 99999-9999"
                {...register("phone_national")}
              />
            </div>
            <FieldError message={errors.phone_national?.message} />
          </div>
          <div>
            <label className={LABEL}>
              E-mail <span className="text-red">*</span>
            </label>
            <input className={FIELD} type="email" {...register("email")} />
            <FieldError message={errors.email?.message} />
            <p className="mt-1 text-xs text-muted">
              É por aqui que enviamos os convites de trabalho.
            </p>
            {/* `hotmail.con` é um email válido para qualquer validador de formato — só um palpite
                sobre o domínio pega o engano antes do envio (feature 219). */}
            {emailTypo && (
              <button
                type="button"
                onClick={() => setValue("email", emailTypo, { shouldValidate: true })}
                className="mt-1 text-xs font-medium text-accent-dark underline"
              >
                Você quis dizer <strong>{emailTypo}</strong>?
              </button>
            )}
          </div>
        </div>
        <CheckboxGroup
          label="Idiomas (com nível suficiente para interagir num evento e/ou cantar)"
          name="languages"
          options={LANGUAGE_OPTIONS}
          required
          register={register}
          error={errors.languages?.message}
        />
        <div>
          <label className={LABEL}>
            Data de nascimento <span className="text-red">*</span>
          </label>
          <input className={FIELD} type="date" {...register("birth_date")} />
          <FieldError message={errors.birth_date?.message} />
        </div>
      </Section>

      <Section title="🪪 Documentos">
        <label className="flex items-center gap-2 text-sm font-medium text-ink">
          <input type="checkbox" className="h-[18px] w-[18px] accent-accent" {...register("is_foreigner")} />
          Sou estrangeiro(a) — não tenho CPF
        </label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <CpfField
            value={cpf}
            onChange={(value) => setValue("cpf", value)}
            disabled={isForeigner}
            error={errors.cpf?.message}
          />
          <div>
            <label className={LABEL}>
              RG / Documento <span className="text-red">*</span>
              {isForeigner && <span className="text-muted"> (passaporte ou documento do seu país)</span>}
            </label>
            <input className={FIELD} {...register("rg")} />
            <FieldError message={errors.rg?.message} />
          </div>
        </div>
        <FileUpload
          label="Foto do seu documento (CPF, RG, CNH ou passaporte)"
          accept={DOC_ACCEPT}
          maxSizeBytes={DOC_MAX_BYTES}
          required
          error={fileErrors.doc_photo}
          onChange={(file) => {
            setFiles((prev) => ({ ...prev, doc_photo: file }));
            setFileErrors((prev) => ({ ...prev, doc_photo: undefined }));
          }}
        />
      </Section>

      <Section title="💸 Pagamento (PIX)">
        <RadioGroup
          label="Tipo de chave PIX"
          name="pix_key_type"
          options={PIX_TYPE_OPTIONS}
          required
          register={register}
          error={errors.pix_key_type?.message}
        />
        <div>
          <label className={LABEL}>
            Chave PIX <span className="text-red">*</span>
          </label>
          <input className={FIELD} {...register("pix_key")} />
          <FieldError message={errors.pix_key?.message} />
        </div>
        <div>
          <label className={LABEL}>Chave PIX (secundária) (opcional)</label>
          <input className={FIELD} {...register("pix_key_secondary")} />
        </div>
      </Section>

      <Section title="📸 Perfil e aparência">
        <RadioGroup
          label="Raça"
          name="race"
          options={RACE_OPTIONS}
          required
          register={register}
          error={errors.race?.message}
        />
        <FileUpload
          label="Foto do rosto (close-up)"
          accept={PHOTO_ACCEPT}
          maxSizeBytes={PHOTO_MAX_BYTES}
          required
          error={fileErrors.photo_face}
          onChange={(file) => {
            setFiles((prev) => ({ ...prev, photo_face: file }));
            setFileErrors((prev) => ({ ...prev, photo_face: undefined }));
          }}
        />
        <FileUpload
          label="Foto de corpo inteiro"
          accept={PHOTO_ACCEPT}
          maxSizeBytes={PHOTO_MAX_BYTES}
          required
          error={fileErrors.photo_full}
          onChange={(file) => {
            setFiles((prev) => ({ ...prev, photo_full: file }));
            setFileErrors((prev) => ({ ...prev, photo_full: undefined }));
          }}
        />
        <div>
          <label className={LABEL}>
            Altura em metros (ex.: 1,75) <span className="text-red">*</span>
          </label>
          <input className={FIELD} placeholder="Ex: 1,75" {...register("height")} />
          <FieldError message={errors.height?.message} />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>
              Manequim/roupa superior <span className="text-red">*</span>
            </label>
            <select className={FIELD} {...register("clothing_top")}>
              <option value="">— selecione —</option>
              {CLOTHING_SIZE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <FieldError message={errors.clothing_top?.message} />
          </div>
          <div>
            <label className={LABEL}>
              Manequim/roupa inferior <span className="text-red">*</span>
            </label>
            <select className={FIELD} {...register("clothing_bottom")}>
              <option value="">— selecione —</option>
              {CLOTHING_SIZE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <FieldError message={errors.clothing_bottom?.message} />
          </div>
        </div>
        <div>
          <label className={LABEL}>
            Tamanho do sapato (numeração brasileira) <span className="text-red">*</span>
          </label>
          <input className={FIELD} inputMode="numeric" placeholder="Ex: 38" {...register("shoe_size")} />
          <FieldError message={errors.shoe_size?.message} />
        </div>
        <RadioGroup
          label="Possui passaporte e visto americano?"
          name="passport"
          options={PASSPORT_OPTIONS}
          required
          register={register}
          error={errors.passport?.message}
        />
      </Section>

      <Section title="🎭 Habilidades" hint="Marque todas as opções que te definem.">
        <CheckboxGroup label="" name="skills" options={SKILL_OPTIONS} register={register} error={errors.skills?.message} />
      </Section>

      <Section title="🚗 Carro e CNH (opcional)" hint="Preencha só se você tem carro e/ou pode dirigir em trabalhos.">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Marca do carro</label>
            <input className={FIELD} {...register("car_brand")} />
          </div>
          <div>
            <label className={LABEL}>Modelo do carro</label>
            <input className={FIELD} {...register("car_model")} />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Ano do carro</label>
            <input className={FIELD} inputMode="numeric" {...register("car_year")} />
          </div>
          <div>
            <label className={LABEL}>Placa do carro</label>
            <input className={FIELD} {...register("car_plate")} />
          </div>
        </div>
        <div>
          <label className={LABEL}>Data de vencimento da CNH</label>
          <input className={FIELD} type="date" {...register("cnh_expiration")} />
        </div>
        <FileUpload
          label="Foto ou arquivo da CNH aberta"
          accept={DOC_ACCEPT}
          maxSizeBytes={DOC_MAX_BYTES}
          error={fileErrors.cnh_file}
          onChange={(file) => {
            setFiles((prev) => ({ ...prev, cnh_file: file }));
            setFileErrors((prev) => ({ ...prev, cnh_file: undefined }));
          }}
        />
      </Section>

      <Button type="submit" size="lg" className="w-full" loading={isSubmitting || submitCadastro.isPending}>
        {submitCadastro.isPending ? "Enviando..." : "Enviar cadastro"}
      </Button>
      <p className="text-center text-xs text-muted">
        Seus dados são usados apenas para o cadastro de talentos da Manto Produções.
      </p>
    </form>
  );
}
