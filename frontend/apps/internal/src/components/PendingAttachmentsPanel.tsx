import { Button, Card, CardContent } from "@manto/ui";

export type AttachmentUploadStatus = "pending" | "uploading" | "success" | "error";

export interface AttachmentUploadItem {
  id: string;
  label: string;
  status: AttachmentUploadStatus;
}

/** Status por anexo pendente após a criação do evento (feature 184, FR-029) — o evento já foi
 * criado com sucesso; este painel garante que uma falha de upload não fique escondida atrás de
 * uma navegação prematura para a tela de detalhe. */
export function PendingAttachmentsPanel({
  items,
  onRetry,
}: {
  items: AttachmentUploadItem[];
  onRetry: (id: string) => void;
}) {
  if (items.length === 0) return null;

  const STATUS_LABEL: Record<AttachmentUploadStatus, string> = {
    pending: "Aguardando…",
    uploading: "Enviando…",
    success: "Enviado ✓",
    error: "Falhou",
  };

  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <p className="text-sm font-medium text-ink">Enviando anexos do evento…</p>
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <li key={item.id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span className="text-ink">{item.label}</span>
              <div className="flex items-center gap-2">
                <span
                  className={
                    item.status === "error"
                      ? "text-red"
                      : item.status === "success"
                        ? "text-green"
                        : "text-muted"
                  }
                >
                  {STATUS_LABEL[item.status]}
                </span>
                {item.status === "error" && (
                  <Button type="button" variant="outline" size="sm" onClick={() => onRetry(item.id)}>
                    Tentar novamente
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
