import { Link } from "react-router-dom";
import { Printer } from "lucide-react";
import { AvatarThumb, Badge, Button } from "@manto/ui";
import { API_BASE, assetUrl } from "@manto/api-client";
import type { EventoDetalhe, RoleItem } from "../../lib/agenda";
import { useLinkFigurinoSheet, useToggleFigurinoDone } from "../../lib/eventDetail";
import { Empty, formatDay, Panel } from "./parts";
import { FigurinoPicker } from "../FigurinoPicker";

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
  const link = useLinkFigurinoSheet(eventId);
  const toggleDone = useToggleFigurinoDone(eventId);

  const manutencao = role.figurino_manutencao;
  const bloqueado = Boolean(manutencao?.impede_uso);

  return (
    <li
      className={`rounded-md border p-3 ${
        // Bloqueio vence o "separado": marcar como separado um boneco que não pode ir seria
        // exatamente o erro que o aviso existe para impedir.
        bloqueado
          ? "border-red bg-red-soft/20"
          : role.figurino_done
            ? "border-green bg-green-soft/20"
            : "border-line bg-surface-2/40"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <AvatarThumb
          src={role.talent?.photo_url ? assetUrl(role.talent.photo_url) : null}
          name={role.talent?.name}
          shape="circle"
          size="lg"
          fallbackIcon="🎭"
        />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-bold uppercase tracking-wide text-ink">
            {role.character_name}
          </div>
          <div className="text-sm text-muted">{role.talent?.name ?? "— sem talento —"}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {role.figurino_sheet_name ? (
              <Badge tone="blue">{role.figurino_sheet_name}</Badge>
            ) : (
              <Badge tone="red">Sem ficha</Badge>
            )}
            {role.figurino_done && (
              <Badge tone="green">Separado {formatDay(role.figurino_done_at)}</Badge>
            )}
            {manutencao && (
              <Badge tone={bloqueado ? "red" : "gold"}>
                {bloqueado
                  ? "⚠ Não pode ir para evento"
                  : `🪡 ${manutencao.abertas} conserto${manutencao.abertas === 1 ? "" : "s"} em aberto`}
              </Badge>
            )}
          </div>
          {/* O relato do defeito, aqui, na hora de separar o figurino — é o único momento em que
              "tem uma peça solta dentro do boneco" muda alguma decisão. */}
          {manutencao && (
            <p className="mt-1 text-xs text-muted">
              {manutencao.titulos.join(" · ")}{" "}
              <Link
                to={`/figurinos/producao?ficha=${role.figurino_sheet_id}`}
                className="text-accent hover:underline"
              >
                ver na oficina
              </Link>
            </p>
          )}
        </div>
        <Medidas role={role} />
      </div>

      {canEdit && (
        <div className="mt-2 space-y-2 sm:flex sm:items-center sm:gap-2 sm:space-y-0">
          <FigurinoPicker
            className="sm:min-w-48 sm:flex-1"
            value={role.figurino_sheet_id}
            characterName={role.character_name}
            disabled={link.isPending}
            ariaLabel={`Ficha de figurino de ${role.character_name}`}
            onChange={(sheetId) => link.mutate({ roleId: role.role_id, sheetId })}
          />
          <label className="flex h-11 items-center gap-2 rounded-md border border-line bg-panel px-3 text-sm text-ink sm:h-9 sm:border-0 sm:bg-transparent sm:px-0">
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
            {toggleDone.isPending && <span className="text-xs text-muted">salvando…</span>}
          </label>
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
          {personagens.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                window.open(
                  `${API_BASE}/figurinos/print-event/${data.event.id}`,
                  "_blank",
                  "noopener",
                )
              }
            >
              <Printer className="h-3.5 w-3.5" aria-hidden="true" />
              Imprimir fichas
            </Button>
          )}
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
