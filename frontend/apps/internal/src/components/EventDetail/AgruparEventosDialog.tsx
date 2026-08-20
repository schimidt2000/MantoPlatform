import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Skeleton,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import { ApiRequestError } from "@manto/api-client";
import {
  useAgruparEventos,
  useCandidatosGrupo,
  type EventoComVenda,
} from "../../lib/eventOps";
import type { EventoDetalhe } from "../../lib/agenda";

const LABEL = "mb-1 block text-xs font-semibold uppercase text-muted";

function dataCurta(iso: string | null): string {
  if (!iso) return "sem data";
  // A string vem "YYYY-MM-DDTHH:MM" e é horário de parede: fatiar evita o deslocamento de fuso
  // que `new Date(...)` introduziria.
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

/**
 * O aviso que aparece quando algum evento marcado tem venda — o passo que impede perda silenciosa.
 *
 * A tela antiga tinha só um checkbox genérico ("confirmo a substituição dos dados"). Aqui a lista
 * vem do 409 do servidor, com nome e valor de cada um, porque quem confirma precisa saber
 * exatamente quanto está apagando.
 */
function AvisoPerdaDeVenda({ eventos }: { eventos: EventoComVenda[] }) {
  return (
    <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="alert">
      <p className="font-semibold text-gold-ink">
        {eventos.length === 1
          ? "Este evento vai perder o valor de venda:"
          : "Estes eventos vão perder o valor de venda:"}
      </p>
      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink">
        {eventos.map((e) => (
          <li key={e.id}>
            {e.title} — <strong>R$ {formatBRL(Number(e.sale_value))}</strong>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-ink">
        A partir do agrupamento, a venda do contrato inteiro fica no evento principal. Desagrupar
        depois <strong>não devolve</strong> esses valores — eles ficam guardados no histórico de
        cada evento, para consulta.
      </p>
    </div>
  );
}

export interface AgruparEventosDialogProps {
  data: EventoDetalhe;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Agrupa este evento com outros sob um mesmo contrato comercial (feature 246).
 *
 * Duas decisões de interface que a tela antiga não tomava: a busca é no servidor (ela despejava
 * os 354 eventos de uma vez no HTML) e o principal pode ser QUALQUER um dos participantes,
 * inclusive um dos marcados — por isso, ao concluir, a página navega para o principal quando ele
 * não é o evento atual: a tela em que a pessoa está pode ter acabado de virar satélite.
 */
export function AgruparEventosDialog({ data, open, onOpenChange }: AgruparEventosDialogProps) {
  const navigate = useNavigate();
  const eventId = data.event.id;

  const [busca, setBusca] = useState("");
  const [buscaDebounced, setBuscaDebounced] = useState("");
  const [marcados, setMarcados] = useState<Record<number, string>>({});
  const [principal, setPrincipal] = useState<number>(eventId);
  const [nomeGrupo, setNomeGrupo] = useState("");
  const [aConfirmar, setAConfirmar] = useState<EventoComVenda[] | null>(null);

  const candidatos = useCandidatosGrupo(eventId, buscaDebounced, open);
  const agrupar = useAgruparEventos(eventId);

  useEffect(() => {
    const t = setTimeout(() => setBuscaDebounced(busca), 300);
    return () => clearTimeout(t);
  }, [busca]);

  // Reabrir o diálogo tem de começar do zero: manter marcação de uma tentativa anterior é o tipo
  // de estado velho que faz alguém agrupar o evento errado.
  useEffect(() => {
    if (!open) {
      setBusca("");
      setBuscaDebounced("");
      setMarcados({});
      setPrincipal(eventId);
      setNomeGrupo("");
      setAConfirmar(null);
      agrupar.reset();
    }
    // `agrupar` é estável entre renders (useMutation); incluí-lo dispararia o reset em loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, eventId]);

  const idsMarcados = Object.keys(marcados).map(Number);

  function alternar(id: number, title: string) {
    setMarcados((atual) => {
      const proximo = { ...atual };
      if (id in proximo) {
        delete proximo[id];
        // Se o principal escolhido saiu da seleção, volta para o evento atual — senão o envio
        // iria com um principal que não participa mais.
        if (principal === id) setPrincipal(eventId);
      } else {
        proximo[id] = title;
      }
      return proximo;
    });
  }

  function enviar(confirmando: boolean) {
    agrupar.mutate(
      {
        leader_event_id: principal,
        target_event_ids: idsMarcados,
        group_name: nomeGrupo.trim() || undefined,
        confirm_clear_financials: confirmando,
      },
      {
        onSuccess: (resposta) => {
          onOpenChange(false);
          if (resposta.leader_id && resposta.leader_id !== eventId) {
            navigate(`/events/${resposta.leader_id}`);
          }
        },
        onError: (erro) => {
          // O 409 de confirmação NÃO é falha: é o servidor devolvendo o que será apagado, para
          // esta tela poder listar nomes e valores antes de a pessoa decidir.
          const detalhes = (erro as ApiRequestError).details;
          const comVenda = detalhes?.events_with_sale as EventoComVenda[] | undefined;
          if (comVenda?.length) setAConfirmar(comVenda);
        },
      },
    );
  }

  const podeEnviar = idsMarcados.length > 0 && !agrupar.isPending;
  const participantes = [{ id: eventId, title: data.event.title }, ...idsMarcados.map((id) => ({ id, title: marcados[id] }))];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Agrupar eventos do mesmo contrato</DialogTitle>
        </DialogHeader>

        {aConfirmar ? (
          <div className="space-y-3">
            <AvisoPerdaDeVenda eventos={aConfirmar} />
            {agrupar.isError && !agrupar.isPending && (
              <p className="text-sm text-red">{agrupar.error?.message}</p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className={LABEL} htmlFor="grupo-busca">
                Procurar eventos para agrupar
              </label>
              <Input
                id="grupo-busca"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Nome do evento, cliente ou personagem"
                autoFocus
              />
              <p className="mt-1 text-xs text-muted">Digite ao menos 2 letras.</p>
            </div>

            {candidatos.isLoading && <Skeleton className="h-24 w-full" />}
            {candidatos.data && candidatos.data.items.length === 0 && buscaDebounced.length >= 2 && (
              <p className="text-sm text-muted">Nenhum evento encontrado para “{buscaDebounced}”.</p>
            )}

            {candidatos.data && candidatos.data.items.length > 0 && (
              <ul className="max-h-56 space-y-1 overflow-y-auto rounded-md border border-line p-1">
                {candidatos.data.items.map((c) => {
                  const bloqueado = Boolean(c.blocked_reason);
                  return (
                    <li key={c.id}>
                      <label
                        className={`flex items-start gap-2 rounded p-2 text-sm ${
                          bloqueado ? "opacity-55" : "cursor-pointer hover:bg-surface-2"
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="mt-1"
                          disabled={bloqueado}
                          checked={c.id in marcados}
                          onChange={() => alternar(c.id, c.title)}
                        />
                        <span>
                          <span className="text-ink">{c.title}</span>
                          <span className="ml-2 text-xs text-muted">{dataCurta(c.start_at)}</span>
                          {c.has_sale && !bloqueado && (
                            <span className="ml-2 text-xs text-gold-ink">tem venda registrada</span>
                          )}
                          {bloqueado && (
                            <span className="ml-2 text-xs text-muted">— {c.blocked_reason}</span>
                          )}
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}

            {idsMarcados.length > 0 && (
              <fieldset>
                <legend className={LABEL}>Qual evento é o principal do contrato</legend>
                <p className="mb-2 text-xs text-muted">
                  É nele que a venda inteira fica. Os outros passam a seguir o principal.
                </p>
                <div className="space-y-1">
                  {participantes.map((p) => (
                    <label key={p.id} className="flex cursor-pointer items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="grupo-principal"
                        checked={principal === p.id}
                        onChange={() => setPrincipal(p.id)}
                      />
                      <span className="text-ink">
                        {p.title}
                        {p.id === eventId && <span className="ml-1 text-xs text-muted">(este)</span>}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            {idsMarcados.length > 0 && (
              <div>
                <label className={LABEL} htmlFor="grupo-nome">
                  Nome do grupo (opcional)
                </label>
                <Input
                  id="grupo-nome"
                  value={nomeGrupo}
                  onChange={(e) => setNomeGrupo(e.target.value)}
                  placeholder="Ex.: Evento Siomar"
                  maxLength={200}
                />
                <p className="mt-1 text-xs text-muted">
                  Sem nome, o grupo aparece pelo título do evento principal.
                </p>
              </div>
            )}

            {agrupar.isError && !aConfirmar && (
              <p className="text-sm text-red">{agrupar.error?.message}</p>
            )}
          </div>
        )}

        <DialogFooter>
          {aConfirmar ? (
            <>
              <Button variant="outline" onClick={() => setAConfirmar(null)}>
                Voltar
              </Button>
              <Button onClick={() => enviar(true)} loading={agrupar.isPending}>
                Agrupar mesmo assim
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancelar
              </Button>
              <Button onClick={() => enviar(false)} disabled={!podeEnviar} loading={agrupar.isPending}>
                Agrupar {idsMarcados.length > 0 ? `(${idsMarcados.length + 1} eventos)` : ""}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
