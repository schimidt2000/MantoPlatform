import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useDeleteMusical,
  useDuplicateMusical,
  useMusicalsGestao,
  type EducaMantoMusical,
  type EducaMantoMusicalBasico,
} from "../lib/educamanto";

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

function temCustos(
  m: EducaMantoMusicalBasico | EducaMantoMusical,
): m is EducaMantoMusical {
  return (m as EducaMantoMusical).margin_1s !== undefined;
}

function MusicalCard({
  musical,
  podeGerir,
  onDuplicate,
  duplicating,
  onDelete,
}: {
  musical: EducaMantoMusicalBasico | EducaMantoMusical;
  podeGerir: boolean;
  onDuplicate: () => void;
  duplicating: boolean;
  onDelete: () => void;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle className="text-base">{musical.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-ink">
          <p>
            <span className="text-muted">Personagens:</span> {musical.num_personagens}
          </p>
          <p>
            <span className="text-muted">Produção:</span> {musical.num_producao}
          </p>
          <p>
            <span className="text-muted">Ensaios:</span> {musical.num_ensaios}
          </p>
        </div>

        {/* Custos e margens só chegam na resposta do SUPERADMIN (FR-028). */}
        {temCustos(musical) && (
          <div className="rounded-md bg-surface-2 p-2 text-xs text-ink">
            <p className="mb-1 font-semibold uppercase text-muted">Custos (só superadmin)</p>
            <p>
              Margens: {musical.margin_1s.toFixed(2)}× · {musical.margin_2s.toFixed(2)}× ·{" "}
              {musical.margin_1s_days.toFixed(2)}× · {musical.margin_2s_days.toFixed(2)}×
            </p>
            <p>
              Cenário: {brl(musical.custo_cenario_1s)} (1S) · Alimentação:{" "}
              {brl(musical.custo_alimentacao_1s)}/pessoa (1S)
            </p>
            <p className="text-muted">
              {musical.items.length} {musical.items.length === 1 ? "item" : "itens"} ·{" "}
              {(musical.discount_pct * 100).toFixed(0)}% desconto após {musical.discount_days}{" "}
              dias · Ensemble {brl(musical.ensemble_1s)} (1S)
            </p>
          </div>
        )}

        <div className="mt-auto flex flex-wrap justify-center gap-2 pt-2">
          <Button asChild size="sm">
            <Link to={`/educamanto?musical_id=${musical.id}`}>Usar</Link>
          </Button>
          {podeGerir && (
            <>
              <Button asChild variant="outline" size="sm">
                <Link to={`/educamanto/musicais/${musical.id}/editar`}>Editar</Link>
              </Button>
              <Button variant="outline" size="sm" loading={duplicating} onClick={onDuplicate}>
                Criar cópia
              </Button>
              <Button variant="ghost" size="sm" onClick={onDelete}>
                Excluir
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function EducaMantoMusicaisPage() {
  const musicalsQuery = useMusicalsGestao();
  const duplicateMusical = useDuplicateMusical();
  const deleteMusical = useDeleteMusical();
  const [confirmarExclusao, setConfirmarExclusao] = useState<
    { id: number; name: string } | null
  >(null);

  const musicals = musicalsQuery.data?.musicals ?? [];
  const podeGerir = musicalsQuery.data?.pode_gerir ?? false;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="EducaManto — Musicais"
        className="mb-0"
        actions={
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm">
              <Link to="/educamanto">‹ Calculadora</Link>
            </Button>
            {podeGerir && (
              <Button asChild size="sm">
                <Link to="/educamanto/musicais/novo">+ Novo musical</Link>
              </Button>
            )}
          </div>
        }
      />

      {musicalsQuery.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-52 w-full" />
          ))}
        </div>
      )}

      {musicalsQuery.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os musicais. Confira se você tem permissão para acessar a
          gestão do EducaManto.
        </div>
      )}

      {musicalsQuery.data && musicals.length === 0 && (
        <p className="text-sm text-muted">Nenhum musical cadastrado ainda.</p>
      )}

      {musicals.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {musicals.map((musical) => (
            <MusicalCard
              key={musical.id}
              musical={musical}
              podeGerir={podeGerir}
              duplicating={duplicateMusical.isPending && duplicateMusical.variables === musical.id}
              onDuplicate={() => duplicateMusical.mutate(musical.id)}
              onDelete={() => setConfirmarExclusao({ id: musical.id, name: musical.name })}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={confirmarExclusao !== null}
        title="Excluir musical"
        description={`Excluir o musical "${confirmarExclusao?.name ?? ""}" definitivamente? Os orçamentos já gerados no histórico não são afetados.`}
        confirmLabel="Excluir"
        destructive
        pending={deleteMusical.isPending}
        error={deleteMusical.isError ? "Não foi possível excluir o musical." : null}
        onConfirm={() => {
          if (!confirmarExclusao) return;
          deleteMusical.mutate(confirmarExclusao.id, {
            onSuccess: () => setConfirmarExclusao(null),
          });
        }}
        onOpenChange={(open) => {
          if (!open) setConfirmarExclusao(null);
        }}
      />
    </div>
  );
}
