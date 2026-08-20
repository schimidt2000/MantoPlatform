import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import {
  REVISAO_ACCEPT,
  useDeleteRevisaoSpace,
  useRevisaoSpace,
  useReviewerOptions,
  useUpdateRevisaoReviewers,
  useUploadRevisaoAssets,
  validateRevisaoFiles,
  type MediaType,
} from "../lib/revisao";
import { UploadProgressBar } from "../components/UploadProgressBar";

const MEDIA_ICON: Record<MediaType, string> = {
  video: "🎬",
  audio: "🎧",
  image: "🖼️",
  pdf: "📄",
};

export function RevisaoSpacePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const navigate = useNavigate();
  const location = useLocation();
  const query = useRevisaoSpace(id);
  const reviewerOptions = useReviewerOptions();
  const upload = useUploadRevisaoAssets(id);
  const updateReviewers = useUpdateRevisaoReviewers(id);
  const deleteSpace = useDeleteRevisaoSpace();

  const [reviewerIds, setReviewerIds] = useState<number[]>([]);
  // Arquivos que a CRIAÇÃO do espaço rejeitou chegam via state da navegação (feature 254) —
  // antes eram descartados no redirect e o material "sumia" sem aviso nenhum.
  const [createErrors, setCreateErrors] = useState<string[]>(
    () => (location.state as { uploadErrors?: string[] } | null)?.uploadErrors ?? [],
  );
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [progress, setProgress] = useState<number | null>(null);

  useEffect(() => {
    if (query.data) setReviewerIds(query.data.reviewer_ids);
  }, [query.data]);

  const toggleReviewer = (uid: number) =>
    setReviewerIds((prev) => (prev.includes(uid) ? prev.filter((r) => r !== uid) : [...prev, uid]));

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-[1200px] space-y-4 p-4 sm:p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-[1200px] p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o espaço.
        </div>
      </div>
    );
  }

  const space = query.data;

  return (
    <div className="mx-auto max-w-[1200px] space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/revisao">‹ Revisão de mídia</Link>
      </Button>

      <PageHeader
        title={space.title}
        subtitle={space.description}
        actions={
          space.can_manage && (
            <Button
              variant="outline"
              size="sm"
              loading={deleteSpace.isPending}
              onClick={() => {
                if (window.confirm(`Excluir o espaço "${space.title}"?`)) {
                  deleteSpace.mutate(space.id, { onSuccess: () => navigate("/revisao") });
                }
              }}
            >
              Excluir espaço
            </Button>
          )
        }
      />

      {createErrors.length > 0 && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-medium">
                {createErrors.length === 1
                  ? "1 arquivo não entrou no espaço:"
                  : `${createErrors.length} arquivos não entraram no espaço:`}
              </p>
              <ul className="mt-1 list-inside list-disc">
                {createErrors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
            <button
              type="button"
              className="shrink-0 text-xs underline"
              onClick={() => {
                setCreateErrors([]);
                navigate(location.pathname + location.search, { replace: true });
              }}
            >
              Entendi
            </button>
          </div>
        </div>
      )}

      {/* Materiais ocupam duas frações e revisores uma: a lista de mídia é o conteúdo que cresce,
          o painel de revisores é uma escolha curta que não precisa de meia tela. */}
      <div className="grid items-start gap-4 [&>*]:min-w-0 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Materiais</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {space.assets.length === 0 ? (
            <p className="text-sm text-muted">Nenhum material enviado ainda.</p>
          ) : (
            <ul className="divide-y divide-line">
              {space.assets.map((asset) => (
                <li key={asset.id} className="flex items-center justify-between gap-2 py-2">
                  <Link
                    to={`/revisao/${space.id}/asset/${asset.id}`}
                    className="flex items-center gap-2 text-sm text-ink hover:underline"
                  >
                    <span>{MEDIA_ICON[asset.media_type]}</span>
                    <span>{asset.original_name || `Material #${asset.id}`}</span>
                    {!asset.is_available && (
                      <span className="text-xs text-muted">(finalizado)</span>
                    )}
                  </Link>
                  {asset.days_left != null && (
                    <span className="text-xs text-muted">{asset.days_left}d restantes</span>
                  )}
                </li>
              ))}
            </ul>
          )}
          {space.can_manage && (
            <div className="space-y-2">
              <label className="mb-1 block text-xs font-medium text-muted">
                Adicionar materiais
              </label>
              <input
                type="file"
                multiple
                accept={REVISAO_ACCEPT}
                className="text-sm text-ink"
                disabled={upload.isPending}
                onChange={(e) => {
                  const files = Array.from(e.target.files ?? []);
                  // Permite reescolher o mesmo arquivo após um erro — sem isto o onChange não
                  // dispara de novo para a mesma seleção.
                  e.target.value = "";
                  if (files.length === 0) return;
                  const problems = validateRevisaoFiles(files);
                  if (problems.length > 0) {
                    setUploadErrors(problems);
                    return;
                  }
                  setUploadErrors([]);
                  setProgress(0);
                  upload.mutate(
                    { files, onProgress: setProgress },
                    {
                      onSettled: () => setProgress(null),
                      onError: (err) =>
                        setUploadErrors([
                          err instanceof ApiRequestError
                            ? err.message
                            : "Falha no envio. Tente novamente.",
                        ]),
                    },
                  );
                }}
              />
              <UploadProgressBar fraction={upload.isPending ? progress : null} />
              {(uploadErrors.length > 0 ||
                (upload.data && upload.data.errors.length > 0)) && (
                <ul className="mt-1 text-xs text-red">
                  {uploadErrors.map((e, i) => (
                    <li key={`c${i}`}>{e}</li>
                  ))}
                  {(upload.data?.errors ?? []).map((e, i) => (
                    <li key={`s${i}`}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {space.can_manage && (
        <Card>
          <CardHeader>
            <CardTitle>Revisores</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {reviewerOptions.data && (
              <div className="flex flex-wrap gap-1.5">
                {reviewerOptions.data.items.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    className={`rounded-md border px-2 py-1 text-xs ${reviewerIds.includes(u.id) ? "border-accent bg-accent-soft text-accent-dark" : "border-line text-ink"}`}
                    onClick={() => toggleReviewer(u.id)}
                  >
                    {u.name}
                  </button>
                ))}
              </div>
            )}
            <Button
              size="sm"
              loading={updateReviewers.isPending}
              onClick={() => updateReviewers.mutate(reviewerIds)}
            >
              Salvar revisores
            </Button>
          </CardContent>
        </Card>
      )}
      </div>
    </div>
  );
}
