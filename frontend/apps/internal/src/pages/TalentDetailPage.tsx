import { useRef, useState, type ReactNode } from "react";
import { useParams, Link } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, MetricBadge, Skeleton } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { formatBRL } from "@manto/money";
import {
  useRemoveTalentPhoto,
  useSaveTalentNotes,
  useTalent,
  useUploadTalentPhoto,
  type TalentPhotoType,
} from "../lib/talents";

function brl(v: number | null | undefined): string {
  return `R$ ${formatBRL(v ?? 0)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-BR");
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

const WARNING_LABELS: Record<string, string> = {
  leve: "Alerta leve",
  moderado: "Alerta moderado",
  grave: "Alerta grave",
};

/** Campo de foto/documento do talento (feature 155) — envio, preview e remoção. */
function TalentPhotoField({
  talentId,
  photoType,
  label,
  url,
  accept,
}: {
  talentId: number;
  photoType: TalentPhotoType;
  label: string;
  url: string | null;
  accept: string;
}) {
  const upload = useUploadTalentPhoto(talentId);
  const remove = useRemoveTalentPhoto(talentId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = (file: File | null) => {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    upload.mutate(
      { photoType, file },
      { onSettled: () => inputRef.current && (inputRef.current.value = "") },
    );
  };

  const displayUrl = preview ?? assetUrl(url ?? undefined);
  const isPdf = !preview && Boolean(url) && url!.toLowerCase().endsWith(".pdf");

  return (
    <div className="space-y-1.5">
      <p className="text-sm font-medium text-ink">{label}</p>
      {displayUrl ? (
        isPdf ? (
          <a
            href={displayUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue underline"
          >
            Abrir PDF
          </a>
        ) : (
          <img src={displayUrl} alt={label} className="h-24 w-24 rounded-md object-cover" />
        )
      ) : (
        <p className="text-sm text-muted">Nenhum arquivo enviado.</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="max-w-[170px] text-xs text-ink"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          aria-label={`Enviar ${label}`}
        />
        {upload.isPending && <span className="text-xs text-muted">Enviando…</span>}
        {url && (
          <Button
            variant="ghost"
            size="sm"
            loading={remove.isPending}
            onClick={() => {
              if (window.confirm(`Remover ${label.toLowerCase()}?`)) {
                setPreview(null);
                remove.mutate(photoType);
              }
            }}
          >
            Remover
          </Button>
        )}
      </div>
      {upload.isError && (
        <p className="text-xs text-red">Formato não aceito ou falha ao enviar.</p>
      )}
    </div>
  );
}

export function TalentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const query = useTalent(id);
  const saveNotes = useSaveTalentNotes(id);
  const [notes, setNotes] = useState<string | null>(null);
  const [warningLevel, setWarningLevel] = useState<string | null>(null);

  const t = query.data?.talent;
  const currentNotes = notes ?? t?.notes ?? "";
  const currentWarning = warningLevel ?? t?.warning_level ?? "";

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/talents">‹ Talentos</Link>
      </Button>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o talento.
        </div>
      )}

      {query.data && t && (
        <>
          <header className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-20 w-20 shrink-0 overflow-hidden rounded-full bg-surface-2">
                {t.photo_face_path ? (
                  <img
                    src={assetUrl(t.photo_face_path)}
                    alt={t.full_name}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-3xl text-muted">
                    👤
                  </div>
                )}
              </div>
              <div>
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
                  {t.status === "pending" && (
                    <MetricBadge tone="gold">Pendente de aprovação</MetricBadge>
                  )}
                </div>
              </div>
            </div>
            {query.data.can_edit && (
              <Button asChild variant="outline" size="sm">
                <Link to={`/talents/${id}/edit`}>Editar</Link>
              </Button>
            )}
          </header>

          <Section title="Contato">
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
          </Section>

          <Section title="Aparência">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <Field label="Altura" value={t.height_cm ? `${t.height_cm} cm` : null} />
              <Field label="Raça" value={t.race} />
              <Field label="Tamanho superior" value={t.clothing_size_top} />
              <Field label="Tamanho inferior" value={t.clothing_size_bottom} />
              <Field label="Calçado" value={t.shoe_size} />
              <Field label="Idiomas" value={t.languages} />
              <Field label="Passaporte/Visto" value={t.passport_status} />
              <Field label="Habilidades" value={t.skills} />
              <Field label="Tags" value={t.tags} />
            </dl>
          </Section>

          <Section title="Documentos e PIX">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <Field label="CPF" value={t.cpf} />
              <Field label="RG" value={t.rg} />
              <Field label="Chave PIX" value={t.pix_key} />
              <Field label="Chave PIX (2ª)" value={t.pix_key_secondary} />
              <Field label="Tipo de chave" value={t.pix_key_type} />
            </dl>
            {query.data.can_edit ? (
              <div className="mt-3 grid grid-cols-2 gap-4 border-t border-line pt-3 sm:grid-cols-4">
                <TalentPhotoField
                  talentId={id}
                  photoType="face"
                  label="Foto de rosto"
                  url={t.photo_face_path}
                  accept="image/jpeg,image/png,image/webp"
                />
                <TalentPhotoField
                  talentId={id}
                  photoType="full"
                  label="Corpo inteiro"
                  url={t.photo_full_path}
                  accept="image/jpeg,image/png,image/webp"
                />
                <TalentPhotoField
                  talentId={id}
                  photoType="doc"
                  label="Documento (CPF/RG)"
                  url={t.doc_photo_path}
                  accept="image/jpeg,image/png,image/webp,application/pdf"
                />
                <TalentPhotoField
                  talentId={id}
                  photoType="cnh"
                  label="CNH"
                  url={t.cnh_file_path}
                  accept="image/jpeg,image/png,image/webp,application/pdf"
                />
              </div>
            ) : (
              <div className="mt-3 flex flex-wrap gap-3">
                {t.photo_full_path && (
                  <a
                    href={assetUrl(t.photo_full_path)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue underline"
                  >
                    Foto de corpo inteiro
                  </a>
                )}
                {t.doc_photo_path && (
                  <a
                    href={assetUrl(t.doc_photo_path)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue underline"
                  >
                    Documento (CPF/RG)
                  </a>
                )}
                {t.cnh_file_path && (
                  <a
                    href={assetUrl(t.cnh_file_path)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue underline"
                  >
                    CNH
                  </a>
                )}
              </div>
            )}
          </Section>

          {(t.car_brand || t.car_model || t.car_plate) && (
            <Section title="Veículo">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <Field label="Marca" value={t.car_brand} />
                <Field label="Modelo" value={t.car_model} />
                <Field label="Ano" value={t.car_year} />
                <Field label="Placa" value={t.car_plate} />
                <Field label="CNH válida até" value={formatDate(t.cnh_expiration)} />
              </dl>
            </Section>
          )}

          <Section title="Anotações internas">
            {query.data.can_edit ? (
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
                  <option value="leve">Alerta leve</option>
                  <option value="moderado">Alerta moderado</option>
                  <option value="grave">Alerta grave</option>
                </select>
                <div>
                  <Button
                    size="sm"
                    loading={saveNotes.isPending}
                    onClick={() =>
                      saveNotes.mutate({ notes: currentNotes, warning_level: currentWarning })
                    }
                  >
                    Salvar anotação
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

          <Section title="Histórico de eventos">
            <p className="mb-2 text-sm text-muted">
              {query.data.history.total_events} evento(s) · total recebido:{" "}
              <span className="tabular-nums text-ink">{brl(query.data.history.total_earned)}</span>
            </p>
            {query.data.history.items.length === 0 ? (
              <p className="text-sm text-muted">Nenhum evento no histórico.</p>
            ) : (
              <ul className="divide-y divide-line">
                {query.data.history.items.map((h, i) => (
                  <li key={i} className="flex items-center justify-between gap-3 py-1.5 text-sm">
                    <div>
                      <span className="text-muted">{formatDate(h.start_at)}</span>{" "}
                      <Link to={`/events/${h.event_id}`} className="text-ink hover:underline">
                        {h.event_title ?? `Evento #${h.event_id}`}
                      </Link>
                      <span className="ml-1 rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                        {h.character_name}
                      </span>
                    </div>
                    <span className="tabular-nums text-ink">{brl(h.cache_value)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </>
      )}
    </div>
  );
}
