/**
 * Barra de progresso de upload (feature 254). Um vídeo de revisão sobe por minutos; sem isto o
 * silêncio parecia conclusão e a aba era fechada no meio do envio. `fraction` vem do
 * `xhr.upload.onprogress` (0..1); `null` esconde a barra.
 */
export function UploadProgressBar({ fraction }: { fraction: number | null }) {
  if (fraction == null) return null;
  const pct = Math.round(fraction * 100);
  return (
    <div aria-live="polite">
      <div className="flex items-center justify-between text-xs text-muted">
        <span>{pct < 100 ? "Enviando… não feche esta página." : "Enviado — processando…"}</span>
        <span>{pct}%</span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full border border-line bg-panel">
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-200"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
