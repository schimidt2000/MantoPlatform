import { useEffect, useId, useState, type ReactNode } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  DenseCard,
  FileUpload,
  MetricBadge,
  Skeleton,
} from "@manto/ui";
import { assetUrl, ApiRequestError } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import {
  useApproveTalent,
  useRejectTalent,
  useRemoveTalentPhoto,
  useSaveTalentNotes,
  useTalent,
  useTalentRatings,
  useUpdateTalent,
  useUploadTalentPhoto,
  type TalentUpdateInput,
} from "../lib/talents";

function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR");
}

function splitValues(raw: string | null | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(/[;,/\n]+/)
    .map((v) => v.trim())
    .filter(Boolean);
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <>
      <dt className="text-muted">{label}</dt>
      <dd className="text-ink">{value}</dd>
    </>
  );
}

function Stars({ score }: { score: number }) {
  return (
    <span className="tabular-nums text-gold" aria-label={`${score} de 5 estrelas`}>
      {"★".repeat(score)}
      <span className="text-line">{"★".repeat(5 - score)}</span>
    </span>
  );
}

const WARNING_LABELS: Record<string, string> = {
  leve: "Alerta leve",
  moderado: "Alerta moderado",
  grave: "Alerta grave",
};

const PASSPORT_LABELS: Record<string, string> = {
  visa: "Passaporte + visto americano",
  passport: "Passaporte sem visto",
  none: "Sem passaporte",
};

const SIZE_OPTIONS = ["XP", "P", "M", "G", "GG", "XGG"];
const SHOE_OPTIONS = Array.from({ length: 15 }, (_, i) => String(33 + i));

const LABEL_CLS = "mb-1 block text-xs font-medium text-muted";
const INPUT_CLS = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

function TextField({
  label,
  value,
  onChange,
  disabled,
  type = "text",
  error,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  type?: string;
  error?: string;
}) {
  const inputId = useId();
  return (
    <div>
      <label htmlFor={inputId} className={LABEL_CLS}>
        {label}
      </label>
      <input
        id={inputId}
        type={type}
        className={INPUT_CLS}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
      {error && <p className="mt-1 text-xs text-red">{error}</p>}
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder = "Não informado",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  const selectId = useId();
  return (
    <div>
      <label htmlFor={selectId} className={LABEL_CLS}>
        {label}
      </label>
      <select
        id={selectId}
        className={INPUT_CLS}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function TalentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const mode: "read" | "edit" = searchParams.get("edit") === "1" ? "edit" : "read";
  const setMode = (next: "read" | "edit") => {
    setSearchParams(
      (prev) => {
        const sp = new URLSearchParams(prev);
        if (next === "edit") sp.set("edit", "1");
        else sp.delete("edit");
        return sp;
      },
      { replace: true },
    );
  };

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const query = useTalent(id, { date_from: dateFrom || undefined, date_to: dateTo || undefined });
  const ratingsQuery = useTalentRatings(id);
  const saveNotes = useSaveTalentNotes(id);
  const updateTalent = useUpdateTalent(id);
  const approve = useApproveTalent();
  const reject = useRejectTalent();
  const uploadPhoto = useUploadTalentPhoto(id);
  const removePhoto = useRemoveTalentPhoto(id);

  const [notes, setNotes] = useState<string | null>(null);
  const [warningLevel, setWarningLevel] = useState<string | null>(null);
  const [form, setForm] = useState<TalentUpdateInput | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const t = query.data?.talent;
  const currentNotes = notes ?? t?.notes ?? "";
  const currentWarning = warningLevel ?? t?.warning_level ?? "";

  useEffect(() => {
    if (mode === "edit" && t && !form) {
      const { id: _id, status: _status, notes: _notes, warning_level: _wl, ...editable } = t;
      setForm(editable);
      setFieldErrors({});
    }
    if (mode === "read" && form) {
      setForm(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, t]);

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }
  if (query.isError || !query.data || !t) {
    return (
      <div className="mx-auto max-w-[1400px] p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o talento.
        </div>
      </div>
    );
  }

  const canEdit = query.data.can_edit;
  const s = (v: string | null | undefined) => v ?? "";
  const setF = <K extends keyof TalentUpdateInput>(key: K, value: TalentUpdateInput[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  const submitEdit = () => {
    if (!form) return;
    setFieldErrors({});
    updateTalent.mutate(form, {
      onSuccess: () => setMode("read"),
      onError: (err) => {
        if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
      },
    });
  };

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Button asChild variant="ghost" size="sm" className="mb-2 -ml-2">
            <Link to={`/talents${t.status === "pending" ? "?status=pending" : ""}`}>
              ‹ {t.status === "pending" ? "Talentos Pendentes" : "Talentos Ativos"}
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold text-ink">{t.full_name}</h1>
          {t.artistic_name && <p className="text-sm text-muted">{t.artistic_name}</p>}
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {(t.height_cm || t.clothing_size_top || t.shoe_size) && (
              <MetricBadge
                items={
                  [
                    t.height_cm ? `${t.height_cm}cm` : null,
                    t.clothing_size_top,
                    t.shoe_size ? `Calçado ${t.shoe_size}` : null,
                  ].filter(Boolean) as string[]
                }
              />
            )}
          </div>
        </div>
        {canEdit && mode === "read" && (
          <Button onClick={() => setMode("edit")}>Editar</Button>
        )}
        {mode === "edit" && (
          <div className="flex gap-2">
            <Button loading={updateTalent.isPending} onClick={submitEdit}>
              Salvar
            </Button>
            <Button variant="outline" onClick={() => setMode("read")}>
              Cancelar
            </Button>
          </div>
        )}
      </header>

      {t.status === "pending" && canEdit && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gold bg-gold-soft px-4 py-3">
          <p className="text-sm font-medium text-ink">
            Cadastro pendente de aprovação — revise os dados antes de aprovar.
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              loading={approve.isPending}
              onClick={() => approve.mutate(id, { onSuccess: () => query.refetch() })}
            >
              ✓ Aprovar
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={reject.isPending}
              onClick={() => {
                if (window.confirm(`Rejeitar o cadastro de "${t.full_name}"? Isso exclui o registro.`)) {
                  reject.mutate(id, { onSuccess: () => navigate("/talents?status=pending") });
                }
              }}
            >
              Rejeitar
            </Button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
        {/* Coluna esquerda — destaque visual */}
        <div className="space-y-4">
          <Card className="overflow-hidden">
            <div className="aspect-[3/4] bg-surface-2">
              {t.photo_face_path ? (
                <img
                  src={assetUrl(t.photo_face_path)}
                  alt={t.full_name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-5xl text-muted">
                  👤
                </div>
              )}
            </div>
            {mode === "edit" && (
              <CardContent className="p-3">
                <FileUpload
                  label="Foto de rosto"
                  accept="image/jpeg,image/png,image/webp"
                  maxSizeBytes={10 * 1024 * 1024}
                  existingUrl={t.photo_face_path ? assetUrl(t.photo_face_path) : null}
                  existingLabel="Foto de rosto enviada"
                  removingExisting={removePhoto.isPending && removePhoto.variables === "face"}
                  onChange={(file) => file && uploadPhoto.mutate({ photoType: "face", file })}
                  onRemoveExisting={() => removePhoto.mutate("face")}
                />
              </CardContent>
            )}
          </Card>

          <Section title="Foto de corpo inteiro">
            {mode === "edit" ? (
              <FileUpload
                label="Corpo inteiro"
                accept="image/jpeg,image/png,image/webp"
                maxSizeBytes={10 * 1024 * 1024}
                existingUrl={t.photo_full_path ? assetUrl(t.photo_full_path) : null}
                existingLabel="Foto de corpo inteiro enviada"
                removingExisting={removePhoto.isPending && removePhoto.variables === "full"}
                onChange={(file) => file && uploadPhoto.mutate({ photoType: "full", file })}
                onRemoveExisting={() => removePhoto.mutate("full")}
              />
            ) : t.photo_full_path ? (
              <img
                src={assetUrl(t.photo_full_path)}
                alt="Corpo inteiro"
                className="max-h-[520px] w-full rounded-md object-contain"
              />
            ) : (
              <p className="text-sm text-muted">Nenhuma foto de corpo inteiro cadastrada.</p>
            )}
          </Section>

          <Section title="Documento com foto (CNH/RG)">
            {mode === "edit" ? (
              <div className="space-y-3">
                <FileUpload
                  label="Documento (CPF/RG)"
                  accept="image/jpeg,image/png,image/webp,application/pdf"
                  maxSizeBytes={10 * 1024 * 1024}
                  existingUrl={t.doc_photo_path ? assetUrl(t.doc_photo_path) : null}
                  existingLabel="Documento enviado"
                  removingExisting={removePhoto.isPending && removePhoto.variables === "doc"}
                  onChange={(file) => file && uploadPhoto.mutate({ photoType: "doc", file })}
                  onRemoveExisting={() => removePhoto.mutate("doc")}
                />
                <FileUpload
                  label="CNH"
                  accept="image/jpeg,image/png,image/webp,application/pdf"
                  maxSizeBytes={10 * 1024 * 1024}
                  existingUrl={t.cnh_file_path ? assetUrl(t.cnh_file_path) : null}
                  existingLabel="CNH enviada"
                  removingExisting={removePhoto.isPending && removePhoto.variables === "cnh"}
                  onChange={(file) => file && uploadPhoto.mutate({ photoType: "cnh", file })}
                  onRemoveExisting={() => removePhoto.mutate("cnh")}
                />
              </div>
            ) : t.doc_photo_path && t.doc_photo_path.toLowerCase().endsWith(".pdf") ? (
              <a
                href={assetUrl(t.doc_photo_path)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue underline"
              >
                Abrir PDF
              </a>
            ) : t.doc_photo_path ? (
              <img
                src={assetUrl(t.doc_photo_path)}
                alt="Documento com foto"
                className="max-h-80 w-full rounded-md object-contain"
              />
            ) : (
              <p className="text-sm text-muted">Nenhum documento cadastrado.</p>
            )}
          </Section>
        </div>

        {/* Coluna direita — dados cadastrais */}
        <div className="space-y-4">
          <Section title="Anotações internas">
            {mode === "edit" ? (
              <div className="space-y-2">
                <textarea
                  className="min-h-20 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
                  placeholder="Anotação interna (não visível ao talento)"
                  value={currentNotes}
                  onChange={(e) => setNotes(e.target.value)}
                />
                <select
                  className="h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                  value={currentWarning}
                  onChange={(e) => setWarningLevel(e.target.value)}
                >
                  <option value="">Sem alerta</option>
                  <option value="leve">Atenção</option>
                  <option value="grave">Bloqueado</option>
                </select>
                <div>
                  <Button
                    size="sm"
                    loading={saveNotes.isPending}
                    onClick={() =>
                      saveNotes.mutate({ notes: currentNotes, warning_level: currentWarning })
                    }
                  >
                    Salvar anotações
                  </Button>
                </div>
                {saveNotes.isError && (
                  <p className="text-sm text-red">Não foi possível salvar a anotação.</p>
                )}
              </div>
            ) : (
              <>
                {t.warning_level && (
                  <p className="mb-1 text-sm font-medium text-red">
                    {WARNING_LABELS[t.warning_level]}
                  </p>
                )}
                <p className="whitespace-pre-wrap text-sm text-ink">
                  {t.notes || "Nenhuma anotação."}
                </p>
              </>
            )}
          </Section>

          <Section title="Contato">
            {mode === "edit" && form ? (
              <div className="grid grid-cols-2 gap-3">
                <TextField label="Telefone" value={s(form.phone)} onChange={(v) => setF("phone", v)} />
                <TextField
                  label="E-mail"
                  value={s(form.email_contact)}
                  onChange={(v) => setF("email_contact", v)}
                />
                <TextField
                  label="Data de nascimento"
                  type="date"
                  value={s(form.birth_date)}
                  onChange={(v) => setF("birth_date", v)}
                />
                <TextField label="Gênero" value={s(form.gender)} onChange={(v) => setF("gender", v)} />
                <TextField
                  label="Como conheceu a Manto"
                  value={s(form.how_found_us)}
                  onChange={(v) => setF("how_found_us", v)}
                />
                <SelectField
                  label="Já trabalhou com a Manto"
                  value={form.worked_before == null ? "" : form.worked_before ? "1" : "0"}
                  onChange={(v) => setF("worked_before", v === "" ? null : v === "1")}
                  options={[
                    { value: "1", label: "Sim" },
                    { value: "0", label: "Não" },
                  ]}
                />
              </div>
            ) : (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <Field label="Telefone" value={t.phone} />
                <Field label="E-mail" value={t.email_contact} />
                <Field label="Nascimento" value={formatDate(t.birth_date)} />
                <Field label="Gênero" value={t.gender} />
                <Field label="Como conheceu" value={t.how_found_us} />
                {t.worked_before != null && (
                  <>
                    <dt className="text-muted">Já trabalhou com a Manto</dt>
                    <dd className="text-ink">{t.worked_before ? "Sim" : "Não"}</dd>
                  </>
                )}
              </dl>
            )}
          </Section>

          <Section title="Documentos e PIX">
            {mode === "edit" && form ? (
              <div className="grid grid-cols-2 gap-3">
                <TextField label="RG" value={s(form.rg)} onChange={(v) => setF("rg", v)} />
                <TextField
                  label="CPF"
                  value={s(form.cpf)}
                  disabled={!canEdit}
                  onChange={(v) => setF("cpf", v)}
                  error={fieldErrors.cpf}
                />
                <TextField
                  label="Chave PIX"
                  value={s(form.pix_key)}
                  onChange={(v) => setF("pix_key", v)}
                />
                <TextField
                  label="Chave PIX (2ª)"
                  value={s(form.pix_key_secondary)}
                  onChange={(v) => setF("pix_key_secondary", v)}
                />
                <TextField
                  label="Tipo de chave PIX"
                  value={s(form.pix_key_type)}
                  onChange={(v) => setF("pix_key_type", v)}
                />
              </div>
            ) : (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <Field label="CPF" value={t.cpf} />
                <Field label="RG" value={t.rg} />
                <Field label="Chave PIX" value={t.pix_key} />
                <Field label="Chave PIX (2ª)" value={t.pix_key_secondary} />
                <Field label="Tipo de chave" value={t.pix_key_type} />
                {t.doc_photo_path && (
                  <>
                    <dt className="text-muted">Documento</dt>
                    <dd>
                      <a
                        href={assetUrl(t.doc_photo_path)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue underline"
                      >
                        Abrir PDF
                      </a>
                    </dd>
                  </>
                )}
              </dl>
            )}
          </Section>

          <Section title="Aparência">
            {mode === "edit" && form ? (
              <div className="grid grid-cols-2 gap-3">
                <TextField
                  label="Altura (cm)"
                  type="number"
                  value={form.height_cm != null ? String(form.height_cm) : ""}
                  onChange={(v) => setF("height_cm", v ? Number(v) : null)}
                />
                <TextField label="Raça" value={s(form.race)} onChange={(v) => setF("race", v)} />
                <SelectField
                  label="Tamanho superior"
                  value={s(form.clothing_size_top)}
                  onChange={(v) => setF("clothing_size_top", v)}
                  options={SIZE_OPTIONS.map((v) => ({ value: v, label: v }))}
                />
                <SelectField
                  label="Tamanho inferior"
                  value={s(form.clothing_size_bottom)}
                  onChange={(v) => setF("clothing_size_bottom", v)}
                  options={SIZE_OPTIONS.map((v) => ({ value: v, label: v }))}
                />
                <SelectField
                  label="Calçado"
                  value={s(form.shoe_size)}
                  onChange={(v) => setF("shoe_size", v)}
                  options={SHOE_OPTIONS.map((v) => ({ value: v, label: v }))}
                />
                <TextField
                  label="Idiomas"
                  value={s(form.languages)}
                  onChange={(v) => setF("languages", v)}
                />
                <SelectField
                  label="Passaporte/Visto"
                  value={s(form.passport_status)}
                  onChange={(v) => setF("passport_status", v)}
                  options={[
                    { value: "visa", label: "Passaporte + visto americano" },
                    { value: "passport", label: "Passaporte sem visto" },
                    { value: "none", label: "Sem passaporte" },
                  ]}
                />
                <TextField label="Habilidades" value={s(form.skills)} onChange={(v) => setF("skills", v)} />
                <TextField label="Tags" value={s(form.tags)} onChange={(v) => setF("tags", v)} />
              </div>
            ) : (
              <div className="space-y-3 text-sm">
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
                  <Field label="Altura" value={t.height_cm ? `${t.height_cm} cm` : null} />
                  <Field label="Raça/Etnia" value={t.race} />
                  <Field label="Tamanho superior" value={t.clothing_size_top} />
                  <Field label="Tamanho inferior" value={t.clothing_size_bottom} />
                  <Field label="Calçado" value={t.shoe_size} />
                  <Field label="Idiomas" value={t.languages} />
                  <Field
                    label="Passaporte/Visto"
                    value={t.passport_status ? PASSPORT_LABELS[t.passport_status] : null}
                  />
                </dl>
                {(() => {
                  const skills = splitValues(t.skills);
                  const chips = skills.length > 0 ? skills : splitValues(t.tags);
                  return (
                    chips.length > 0 && (
                      <div>
                        <p className="mb-1 text-muted">Habilidades</p>
                        <div className="flex flex-wrap gap-1.5">
                          {chips.map((chip) => (
                            <MetricBadge key={chip} tone="gold">
                              {chip}
                            </MetricBadge>
                          ))}
                        </div>
                      </div>
                    )
                  );
                })()}
              </div>
            )}
          </Section>

          {(mode === "edit" ||
            t.car_brand ||
            t.car_model ||
            t.car_plate ||
            t.car_year ||
            t.cnh_expiration) && (
            <Section title="Veículo">
              {mode === "edit" && form ? (
                <div className="grid grid-cols-2 gap-3">
                  <TextField
                    label="Marca"
                    value={s(form.car_brand)}
                    onChange={(v) => setF("car_brand", v)}
                  />
                  <TextField
                    label="Modelo"
                    value={s(form.car_model)}
                    onChange={(v) => setF("car_model", v)}
                  />
                  <TextField label="Ano" value={s(form.car_year)} onChange={(v) => setF("car_year", v)} />
                  <TextField label="Placa" value={s(form.car_plate)} onChange={(v) => setF("car_plate", v)} />
                  <TextField
                    label="CNH válida até"
                    type="date"
                    value={s(form.cnh_expiration)}
                    onChange={(v) => setF("cnh_expiration", v)}
                  />
                </div>
              ) : (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <Field label="Marca" value={t.car_brand} />
                  <Field label="Modelo" value={t.car_model} />
                  <Field label="Ano" value={t.car_year} />
                  <Field label="Placa" value={t.car_plate} />
                  <Field label="CNH válida até" value={formatDate(t.cnh_expiration)} />
                </dl>
              )}
            </Section>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Section title="Histórico de eventos">
          <div className="mb-3 flex flex-wrap items-end gap-2">
            <div>
              <label className="mb-1 block text-xs text-muted">De</label>
              <input
                type="date"
                className="h-8 rounded-md border border-line bg-panel px-2 text-xs text-ink"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Até</label>
              <input
                type="date"
                className="h-8 rounded-md border border-line bg-panel px-2 text-xs text-ink"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
            {(dateFrom || dateTo) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDateFrom("");
                  setDateTo("");
                }}
              >
                Limpar período
              </Button>
            )}
          </div>
          <DenseCard
            className="mb-3"
            stats={[
              { label: "Eventos", value: query.data.history.total_events },
              { label: "Personagens", value: query.data.history.characters_done.length },
              { label: "Total Faturado", value: brl(query.data.history.total_earned) },
              {
                label: "Último Evento",
                value: query.data.history.last_event
                  ? formatDate(query.data.history.last_event.start_at)
                  : "—",
              },
            ]}
          />
          {query.data.history.items.length === 0 ? (
            <p className="text-sm text-muted">Nenhum evento no histórico.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs text-muted">
                    <th className="py-1.5 pr-3 font-medium">Data</th>
                    <th className="py-1.5 pr-3 font-medium">Evento</th>
                    <th className="py-1.5 pr-3 font-medium">Personagem</th>
                    <th className="py-1.5 pr-3 font-medium">Cachê</th>
                    <th className="py-1.5 font-medium">Ação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {query.data.history.items.map((h, i) => (
                    <tr key={i}>
                      <td className="whitespace-nowrap py-2 pr-3 text-muted">
                        {formatDate(h.start_at)}
                      </td>
                      <td className="py-2 pr-3 text-ink">{h.event_title ?? `Evento #${h.event_id}`}</td>
                      <td className="py-2 pr-3">
                        <span className="inline-block rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                          {h.character_name}
                        </span>
                      </td>
                      <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-ink">
                        {brl(h.cache_value)}
                      </td>
                      <td className="whitespace-nowrap py-2">
                        <Link to={`/events/${h.event_id}`} className="text-sm text-blue underline">
                          Ver evento
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <Section title="Avaliações e Notas">
          {ratingsQuery.isLoading && <Skeleton className="h-20 w-full" />}
          {ratingsQuery.data && (
            <div className="space-y-4">
              {!ratingsQuery.data.show_authors && (
                <p className="text-xs text-muted">Avaliações anônimas — autoria não exibida.</p>
              )}
              <div>
                <h4 className="mb-1.5 text-sm font-medium text-ink">Recebidas dos colegas</h4>
                {ratingsQuery.data.received.length === 0 ? (
                  <p className="text-sm text-muted">Nenhuma avaliação recebida ainda.</p>
                ) : (
                  <ul className="space-y-2">
                    {ratingsQuery.data.received.map((r, i) => (
                      <li key={i} className="rounded-md border border-line p-2 text-sm">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-ink">{r.category_label}</span>
                          <Stars score={r.score} />
                        </div>
                        {r.comment && <p className="mt-1 text-ink">{r.comment}</p>}
                        <p className="mt-1 text-xs text-muted">
                          {r.author} · {r.event_title ?? `Evento #${r.event_id}`} ·{" "}
                          {formatDate(r.event_date)}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h4 className="mb-1.5 text-sm font-medium text-ink">
                  Avaliações gerais feitas por {t.full_name}
                </h4>
                {ratingsQuery.data.given.length === 0 ? (
                  <p className="text-sm text-muted">Nenhuma avaliação dada ainda.</p>
                ) : (
                  <ul className="space-y-2">
                    {ratingsQuery.data.given.map((r, i) => (
                      <li key={i} className="rounded-md border border-line p-2 text-sm">
                        <div className="flex items-center justify-between gap-2">
                          <Stars score={r.score} />
                          {r.edited && <span className="text-xs text-muted">editada</span>}
                        </div>
                        {r.comment && <p className="mt-1 text-ink">{r.comment}</p>}
                        <p className="mt-1 text-xs text-muted">
                          {r.event_title ?? `Evento #${r.event_id}`} · {formatDate(r.event_date)}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}
