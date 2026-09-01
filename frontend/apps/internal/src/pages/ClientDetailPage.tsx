import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  PageHeader,
  Skeleton,
  StarRating,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import {
  useClientDetail,
  useClientFeedback,
  useDeleteClient,
  useUpdateClient,
} from "../lib/clientes";
import { useCurrentUser } from "../lib/useAuth";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  // Pelo texto, nunca por `new Date()`: data-só ("2025-12-20") interpretada como UTC
  // deslocaria um dia para trás no fuso de São Paulo; start_at é horário de parede naive.
  const [year, month, day] = iso.slice(0, 10).split("-");
  if (!year || !month || !day) return "";
  return `${day}/${month}/${year}`;
}

export function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const navigate = useNavigate();
  const query = useClientDetail(id);
  const update = useUpdateClient(id);
  const del = useDeleteClient();
  const { data: user } = useCurrentUser();

  const [cpf, setCpf] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [address, setAddress] = useState("");

  useEffect(() => {
    if (query.data) {
      setCpf(query.data.cpf);
      setCnpj(query.data.cnpj);
      setAddress(query.data.address);
    }
  }, [query.data]);

  const canDelete = Boolean(user?.is_superadmin || user?.roles.includes("FINANCEIRO"));

  return (
    <div className="mx-auto max-w-[1200px] space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/clientes">‹ Clientes</Link>
      </Button>

      {query.isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o cliente.
        </div>
      )}

      {query.data && (
        <>
          <PageHeader
            title={query.data.name}
            subtitle={[query.data.phone_display, query.data.company].filter(Boolean).join(" · ")}
            actions={
              canDelete && (
                <Button
                  variant="outline"
                  size="sm"
                  loading={del.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Excluir o cliente "${query.data.name}"? Os eventos associados serão desvinculados, não excluídos.`,
                      )
                    ) {
                      del.mutate(id, { onSuccess: () => navigate("/clientes") });
                    }
                  }}
                >
                  Excluir
                </Button>
              )
            }
          />

          {/* Cadastro à esquerda, histórico de eventos à direita: a lista de eventos cresce sem
              empurrar os campos de edição para fora da tela. */}
          <div className="grid items-start gap-4 [&>*]:min-w-0 lg:grid-cols-2">
          <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Contato</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-muted">Telefone</dt>
                <dd className="text-ink">{query.data.phone_display}</dd>
                {query.data.email && (
                  <>
                    <dt className="text-muted">E-mail</dt>
                    <dd className="text-ink">{query.data.email}</dd>
                  </>
                )}
                {query.data.company && (
                  <>
                    <dt className="text-muted">Empresa</dt>
                    <dd className="text-ink">{query.data.company}</dd>
                  </>
                )}
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>CPF/CNPJ e endereço</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                  placeholder="CPF"
                  value={cpf}
                  onChange={(e) => setCpf(e.target.value)}
                  aria-label="CPF"
                />
                <input
                  className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                  placeholder="CNPJ"
                  value={cnpj}
                  onChange={(e) => setCnpj(e.target.value)}
                  aria-label="CNPJ"
                />
              </div>
              <textarea
                className="min-h-16 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
                placeholder="Endereço"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                aria-label="Endereço"
              />
              <div>
                <Button
                  size="sm"
                  loading={update.isPending}
                  onClick={() => update.mutate({ cpf, cnpj, address })}
                >
                  Salvar
                </Button>
              </div>
              {update.isError && (
                <p className="text-sm text-red">Não foi possível salvar os dados.</p>
              )}
            </CardContent>
          </Card>
          </div>

          <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Eventos</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-2 text-sm text-muted">
                {query.data.event_count} evento(s) · total vendido:{" "}
                <span className="tabular-nums text-ink">
                  R$ {formatBRL(query.data.total_sales)}
                </span>
              </p>
              {query.data.events.length === 0 ? (
                <p className="text-sm text-muted">Nenhum evento associado.</p>
              ) : (
                <ul className="divide-y divide-line">
                  {query.data.events.map((e) => (
                    <li
                      key={e.id}
                      className="flex items-center justify-between gap-3 py-1.5 text-sm"
                    >
                      <div>
                        <span className="text-muted">{formatDate(e.start_at)}</span>{" "}
                        <Link to={`/events/${e.id}`} className="text-ink hover:underline">
                          {e.title}
                        </Link>
                      </div>
                      <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                        {e.relation}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* Festas registradas em formulário — inclui as anteriores à agenda de 2026, que
              não existem como evento. É o histórico usado para marketing de recompra. */}
          <Card>
            <CardHeader>
              <CardTitle>Festas anteriores (formulários)</CardTitle>
            </CardHeader>
            <CardContent>
              {query.data.form_history.length === 0 ? (
                <p className="text-sm text-muted">Nenhum formulário preenchido por esta cliente.</p>
              ) : (
                <ul className="divide-y divide-line">
                  {query.data.form_history.map((f) => (
                    <li
                      key={f.id}
                      className="flex items-center justify-between gap-3 py-1.5 text-sm"
                    >
                      <div className="min-w-0">
                        <span className="text-muted">
                          {f.event_date ? formatDate(f.event_date) : "sem data"}
                        </span>{" "}
                        {f.event_id && f.event_title ? (
                          <Link to={`/events/${f.event_id}`} className="text-ink hover:underline">
                            {f.event_title}
                          </Link>
                        ) : (
                          <Link
                            to={`/formularios?resposta=${f.id}`}
                            className="text-ink hover:underline"
                          >
                            {f.form_type_label}
                          </Link>
                        )}
                      </div>
                      <span className="shrink-0 rounded-md bg-surface-2 px-1.5 py-0.5 text-xs text-muted">
                        {f.event_id ? "na agenda" : "só formulário"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* Montado só dentro do bloco de dados carregados: com `:id` inválido o
              `client_id` cairia da query string (o hook não tem `enabled`) e o card mostraria
              as avaliações de TODAS as clientes na ficha de uma. */}
          <AvaliacoesCard clientId={query.data.id} />
          </div>
          </div>
        </>
      )}
    </div>
  );
}

function scoreTone(score: number): "green" | "gold" | "red" {
  if (score >= 5) return "green";
  if (score >= 4) return "gold";
  return "red";
}

/**
 * Avaliações que esta cliente deu depois dos eventos (feature 266).
 *
 * Consome o endpoint que já existia com o filtro `client_id` que já era aceito pelo servidor e
 * que nenhuma tela usava. Zero código novo de backend.
 *
 * ⚠️ O recorte do servidor é por `CalendarEvent.client_id` — o FK do **contratante** — enquanto
 * o card "Eventos" acima lista pela associação múltipla `EventClient`. Uma cliente que entra num
 * evento só como assessora aparece lá e não aparece aqui; por isso o estado vazio diz de quais
 * eventos ele fala, em vez de sugerir que ela nunca avaliou. Unificar os dois recortes mudaria a
 * semântica da tela `/clientes/avaliacoes` inteira e pede feature própria.
 */
function AvaliacoesCard({ clientId }: { clientId: number }) {
  const query = useClientFeedback({ period: "all", client_id: clientId });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Avaliações</CardTitle>
      </CardHeader>
      <CardContent>
        {query.isLoading && <Skeleton className="h-20 w-full" />}

        {query.isError && (
          <div className="rounded-md bg-red-soft px-3 py-2 text-sm text-red" role="alert">
            Não foi possível carregar as avaliações.{" "}
            <button
              type="button"
              onClick={() => void query.refetch()}
              className="underline hover:no-underline"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {query.data &&
          (query.data.feedbacks.length === 0 ? (
            <p className="text-sm text-muted">
              Nenhuma avaliação nos eventos em que ela é a contratante.
            </p>
          ) : (
            <>
              <div className="mb-3 flex items-center gap-2 text-sm text-muted">
                <StarRating value={query.data.kpis.media_geral} size="sm" />
                <span className="tabular-nums">
                  {query.data.kpis.media_geral.toFixed(1)}/5 ·{" "}
                  {query.data.kpis.total_avaliacoes}{" "}
                  {query.data.kpis.total_avaliacoes === 1 ? "avaliação" : "avaliações"}
                </span>
              </div>
              <ul className="divide-y divide-line">
                {query.data.feedbacks.map((f) => (
                  <li key={f.id} className="py-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Badge tone={scoreTone(f.score)}>{f.score}/5</Badge>
                      {f.event && (
                        <Link
                          to={`/events/${f.event.id}`}
                          className="truncate text-ink hover:underline"
                        >
                          {f.event.title}
                        </Link>
                      )}
                    </div>
                    {f.comment && <p className="mt-1 text-muted">{f.comment}</p>}
                  </li>
                ))}
              </ul>
            </>
          ))}
      </CardContent>
    </Card>
  );
}
