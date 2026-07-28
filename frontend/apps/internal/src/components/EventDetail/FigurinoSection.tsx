import { useId, useMemo, useState } from "react";
import { Badge, Button } from "@manto/ui";
import type { EventoDetalhe, RoleItem } from "../../lib/agenda";
import { useLinkFigurinoSheet, useToggleFigurinoDone } from "../../lib/eventDetail";
import { useFigurinoSheets } from "../../lib/figurino";
import { Empty, formatDay, INPUT_CLASS, Panel } from "./parts";

/** Medidas do talento, na ordem em que a produção usa para separar o figurino. */
function Medidas({ role }: { role: RoleItem }) {
  const talent = role.talent;
  if (!talent) return null;
  const linhas: [string, string | null][] = [
    ["Top", talent.size_top],
    ["Bottom", talent.size_bottom],
    ["Sapato", talent.shoe_size],
  ];
  return (
    <dl className="text-xs text-muted">
      {linhas.map(([label, value]) => (
        <div key={label} className="flex gap-1">
          <dt>{label}:</dt>
          <dd className="font-medium text-ink">{value || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

interface FigurinoRowProps {
  role: RoleItem;
  eventId: number;
  canEdit: boolean;
}

/**
 * Card compacto de figurino de um personagem: medidas do talento, ficha vinculada (ou o
 * alerta "Sem ficha") e a caixa "Separado" que registra a conferência física no acervo.
 */
function FigurinoRow({ role, eventId, canEdit }: FigurinoRowProps) {
  const sheetsQuery = useFigurinoSheets();
  const link = useLinkFigurinoSheet(eventId);
  const toggleDone = useToggleFigurinoDone(eventId);
  const [busca, setBusca] = useState("");
  const listId = useId();

  const sugestoes = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    const items = sheetsQuery.data?.items ?? [];
    if (!termo) return items.slice(0, 8);
    return items.filter((s) => s.character_name.toLowerCase().includes(termo)).slice(0, 8);
  }, [busca, sheetsQuery.data]);

  const vincular = (name: string) => {
    const sheet = (sheetsQuery.data?.items ?? []).find((s) => s.character_name === name);
    if (!sheet) return;
    link.mutate({ roleId: role.role_id, sheetId: sheet.id }, { onSuccess: () => setBusca("") });
  };

  return (
    <li
      className={`rounded-md border p-3 ${
        role.figurino_done ? "border-green bg-green-soft/20" : "border-line bg-surface-2/40"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-bold uppercase tracking-wide text-ink">
            {role.character_name}
          </div>
          <div className="text-sm text-muted">{role.talent?.name ?? "— sem talento —"}</div>
        </div>
        <Medidas role={role} />
        <div className="flex flex-col items-end gap-1">
          {role.figurino_sheet_name ? (
            <Badge tone="blue">{role.figurino_sheet_name}</Badge>
          ) : (
            <Badge tone="red">Sem ficha</Badge>
          )}
          {role.figurino_done && (
            <Badge tone="green">Separado {formatDay(role.figurino_done_at)}</Badge>
          )}
        </div>
      </div>

      {canEdit && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <label className="min-w-40 flex-1">
            <span className="sr-only">Buscar figurino para {role.character_name}</span>
            <input
              className={INPUT_CLASS}
              list={listId}
              placeholder="Buscar figurino…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              onBlur={(e) => e.target.value && vincular(e.target.value)}
              disabled={link.isPending}
            />
            <datalist id={listId}>
              {sugestoes.map((sheet) => (
                <option key={sheet.id} value={sheet.character_name} />
              ))}
            </datalist>
          </label>
          {role.figurino_sheet_id && (
            <Button
              variant="ghost"
              size="sm"
              loading={link.isPending}
              onClick={() => link.mutate({ roleId: role.role_id, sheetId: null })}
            >
              Desvincular
            </Button>
          )}
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={role.figurino_done}
              disabled={toggleDone.isPending}
              onChange={(e) =>
                toggleDone.mutate({ roleId: role.role_id, done: e.target.checked })
              }
            />
            Separado
          </label>
          {toggleDone.isPending && <span className="text-xs text-muted">Salvando…</span>}
        </div>
      )}
      {link.isError && <p className="mt-1 text-sm text-red">Não foi possível vincular a ficha.</p>}
    </li>
  );
}

export interface FigurinoSectionProps {
  data: EventoDetalhe;
}

/**
 * Figurino do evento (feature 190) — um card por personagem, ligando o catálogo de fichas ao
 * controle físico do acervo. Visível a quem vê figurino; a edição segue o mesmo gate de
 * escrita do evento aplicado pelo servidor.
 */
export function FigurinoSection({ data }: FigurinoSectionProps) {
  const personagens = (data.elenco ?? []).filter((r) => r.role_type !== "extra");
  const canEdit = Boolean(data.flags.show_figurino);
  const semFicha = personagens.filter((r) => !r.figurino_sheet_id).length;

  return (
    <Panel
      title="Figurino"
      actions={
        <>
          {semFicha > 0 && <Badge tone="red">{semFicha} sem ficha</Badge>}
          <Button asChild variant="outline" size="sm">
            <a href="/figurinos">Banco de figurinos</a>
          </Button>
        </>
      }
    >
      {personagens.length === 0 ? (
        <Empty>Nenhum personagem no evento.</Empty>
      ) : (
        <ul className="space-y-2">
          {personagens.map((role) => (
            <FigurinoRow
              key={role.role_id}
              role={role}
              eventId={data.event.id}
              canEdit={canEdit}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}
