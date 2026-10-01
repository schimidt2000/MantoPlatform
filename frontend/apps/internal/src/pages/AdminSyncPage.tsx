import { useState } from "react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  PageHeader,
  Skeleton,
  cn,
} from "@manto/ui";
import { useAdminSyncStatus, useRunSync, type SyncRunResult } from "../lib/adminConfig";

type LinhaDoMes = SyncRunResult["results"][number];

/** Os números de um mês, na ordem e com os rótulos da mensagem do servidor (feature 303). */
const NUMEROS_DO_MES: { chave: keyof LinhaDoMes; rotulo: string }[] = [
  { chave: "removed", rotulo: "removido(s)" },
  { chave: "marcados", rotulo: "mantido(s) e marcado(s)" },
  { chave: "movidos", rotulo: "com data atualizada" },
  { chave: "desmarcados", rotulo: "de volta ao Google Agenda" },
  { chave: "inconclusivos", rotulo: "sem confirmação do Google" },
  { chave: "falhas", rotulo: "com falha" },
];

// `sync_now` não traz esses campos: ausente conta como zero.
const numero = (linha: LinhaDoMes, chave: keyof LinhaDoMes) => Number(linha[chave] ?? 0);

/** `2026-09: 1 removido(s), 2 mantido(s) e marcado(s)` — ou `null` quando o mês não teve nada. */
function textoDoMes(linha: LinhaDoMes): string | null {
  if (!linha.ok && linha.err) return `${linha.ym}: não foi possível consultar o Google Agenda`;
  const partes = NUMEROS_DO_MES.filter(({ chave }) => numero(linha, chave) > 0).map(
    ({ chave, rotulo }) => `${numero(linha, chave)} ${rotulo}`,
  );
  return partes.length ? `${linha.ym}: ${partes.join(", ")}` : null;
}

/** Falha, evento sem confirmação ou mês com erro pedem atenção — a caixa sai no tom de alerta. */
function pedeAtencao(resultado: SyncRunResult): boolean {
  return resultado.results.some(
    (linha) =>
      Boolean(linha.err) || numero(linha, "falhas") > 0 || numero(linha, "inconclusivos") > 0,
  );
}

export function AdminSyncPage() {
  const query = useAdminSyncStatus();
  const runSync = useRunSync();
  const [confirmarLimpeza, setConfirmarLimpeza] = useState(false);
  const resultado = runSync.data;
  const linhas = resultado
    ? resultado.results.map(textoDoMes).filter((linha): linha is string => linha !== null)
    : [];

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
<PageHeader title="Sync da agenda" className="mb-0" />

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          loading={runSync.isPending}
          onClick={() => runSync.mutate("sync_now")}
        >
          Sincronizar agora
        </Button>
        <Button
          variant="outline"
          size="sm"
          loading={runSync.isPending}
          onClick={() => {
            runSync.reset();
            setConfirmarLimpeza(true);
          }}
        >
          Limpar eventos fantasma
        </Button>
      </div>

      {resultado && (
        <div
          className={cn(
            "rounded-md px-4 py-3 text-sm",
            pedeAtencao(resultado) ? "bg-gold-soft text-gold-ink" : "bg-accent-soft text-accent-dark",
          )}
        >
          <p>{resultado.message}</p>
          {linhas.length > 0 && (
            <ul className="mt-2 space-y-0.5 tabular-nums">
              {linhas.map((linha) => (
                <li key={linha}>{linha}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {runSync.isError && !confirmarLimpeza && (
        <p className="text-sm text-red">Não foi possível concluir a ação.</p>
      )}

      <ConfirmDialog
        open={confirmarLimpeza}
        title="Limpar eventos fantasma?"
        description="O sistema confere no Google Agenda cada evento que não aparece na lista do mês, em todos os meses que têm evento no banco. Evento vazio que sumiu é removido. Evento com venda, comprovante, contrato, escala ou grupo fica e é marcado. Evento que só mudou de data é atualizado."
        confirmLabel="Limpar"
        pending={runSync.isPending}
        error={runSync.isError ? runSync.error?.message || "Não foi possível concluir a ação." : null}
        onConfirm={() =>
          runSync.mutate("cleanup_past", { onSuccess: () => setConfirmarLimpeza(false) })
        }
        onOpenChange={setConfirmarLimpeza}
      />

      {query.isLoading && <Skeleton className="h-64 w-full" />}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o status de sync.
        </div>
      )}

      {query.data && (
        <Card>
          <CardHeader>
            <CardTitle>Meses com eventos no banco</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-line text-sm">
              {query.data.months.map((m) => (
                <li key={m.ym} className="flex items-center justify-between py-1.5">
                  <span className="text-ink">
                    {m.ym} ({m.count} evento(s))
                  </span>
                  <span className={m.fresh ? "text-green" : "text-muted"}>
                    {m.age_min != null ? `${m.age_min} min atrás` : "nunca sincronizado"}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
