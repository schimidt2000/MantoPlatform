import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader } from "@manto/ui";
import { useCreateRevisaoSpace, useReviewerOptions } from "../lib/revisao";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

export function RevisaoSpaceCreatePage() {
  const navigate = useNavigate();
  const reviewerOptions = useReviewerOptions();
  const create = useCreateRevisaoSpace();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [reviewerIds, setReviewerIds] = useState<number[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);

  const toggleReviewer = (id: number) =>
    setReviewerIds((prev) => (prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]));

  const handleSubmit = () => {
    setError(null);
    create.mutate(
      { title, description, reviewerIds, files },
      {
        onSuccess: (result) => navigate(`/revisao/${result.id}?novo=1`),
        onError: (err) => {
          setError(err instanceof ApiRequestError ? err.message : "Não foi possível criar o espaço.");
        },
      },
    );
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/revisao">‹ Revisão de mídia</Link>
      </Button>

      <PageHeader title="Novo espaço de revisão" className="mb-0" />

      <Card>
        <CardHeader>
          <CardTitle>Dados</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className={LABEL}>Título</label>
            <input className={INPUT} value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className={LABEL}>Descrição (opcional)</label>
            <textarea
              className="min-h-16 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Revisores</CardTitle>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Materiais</CardTitle>
        </CardHeader>
        <CardContent>
          <input
            type="file"
            multiple
            accept="video/*,audio/*,image/*,application/pdf"
            className="text-sm text-ink"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          />
          {files.length > 0 && (
            <ul className="mt-2 text-xs text-muted">
              {files.map((f, i) => (
                <li key={i}>{f.name}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {error && <p className="text-sm text-red">{error}</p>}
      <Button loading={create.isPending} onClick={handleSubmit}>
        Criar espaço
      </Button>
    </div>
  );
}
