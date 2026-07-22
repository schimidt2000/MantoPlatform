import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import {
  useDeleteRevisaoSpace,
  useRevisaoSpace,
  useReviewerOptions,
  useUpdateRevisaoReviewers,
  useUploadRevisaoAssets,
  type MediaType,
} from "../lib/revisao";

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
  const query = useRevisaoSpace(id);
  const reviewerOptions = useReviewerOptions();
  const upload = useUploadRevisaoAssets(id);
  const updateReviewers = useUpdateRevisaoReviewers(id);
  const deleteSpace = useDeleteRevisaoSpace();

  const [reviewerIds, setReviewerIds] = useState<number[]>([]);

  useEffect(() => {
    if (query.data) setReviewerIds(query.data.reviewer_ids);
  }, [query.data]);

  const toggleReviewer = (uid: number) =>
    setReviewerIds((prev) => (prev.includes(uid) ? prev.filter((r) => r !== uid) : [...prev, uid]));

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-2xl p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o espaço.
        </div>
      </div>
    );
  }

  const space = query.data;

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/revisao">‹ Revisão de mídia</Link>
      </Button>

      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{space.title}</h1>
          {space.description && <p className="text-sm text-muted">{space.description}</p>}
        </div>
        {space.can_manage && (
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
        )}
      </header>

      <Card>
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
            <div>
              <label className="mb-1 block text-xs font-medium text-muted">
                Adicionar materiais
              </label>
              <input
                type="file"
                multiple
                accept="video/*,audio/*,image/*,application/pdf"
                className="text-sm text-ink"
                onChange={(e) => {
                  const files = Array.from(e.target.files ?? []);
                  if (files.length > 0) upload.mutate(files);
                }}
              />
              {upload.data && upload.data.errors.length > 0 && (
                <ul className="mt-1 text-xs text-red">
                  {upload.data.errors.map((e, i) => (
                    <li key={i}>{e}</li>
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
  );
}
