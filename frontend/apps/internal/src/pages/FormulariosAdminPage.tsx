import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  MetricBadge,
  PageHeader,
  Skeleton,
  Tabs,
  TabsList,
  TabsTrigger,
} from "@manto/ui";
import { FormFieldEditor } from "../components/FormFieldEditor";
import { useClientSearch } from "../lib/clientes";
import { useGastosEventos } from "../lib/gastos";
import { useCurrentUser } from "../lib/useAuth";
import {
  useAssociateClient,
  useDeleteFormResponse,
  useDissociateClient,
  useFormResponseDetail,
  useFormResponses,
  useLinkEvent,
  useSearchFormResponses,
  useUnlinkEvent,
  type FormResponseSummary,
} from "../lib/formulariosAdmin";

type FormType = "comum" | "corporativo";
type FormFilter = FormType | "todos";

/** Os dois formulários públicos, na mesma ordem da tela antiga. */
const PUBLIC_FORMS: { formType: FormType; slug: string; nome: string; descricao: string }[] = [
  {
    formType: "comum",
    slug: "pre-contrato",
    nome: "Pré-Contrato (comum)",
    descricao: "Festas e eventos de pessoa física",
  },
  {
    formType: "corporativo",
    slug: "corporativo",
    nome: "Contrato Corporativo",
    descricao: "Empresas / pessoa jurídica",
  },
];

const CONTROL =
  "flex h-11 w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink " +
  "placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/**
 * URL pública do formulário — o link CURTO `/f/<slug>` é o canônico: é o que está impresso
 * em bio/integrações desde a era Jinja, e `frontend/server.js` o redireciona (302,
 * preservando query) para o formulário React da vitrine em `/catalogo/f/<slug>`. Copiar
 * sempre o curto mantém um endereço único em circulação. No dev server do `apps/internal`
 * (:5173) o redirect não existe — copiar/abrir aqui é para conferência visual.
 */
function publicFormUrl(slug: string): string {
  return `${window.location.origin}/f/${slug}`;
}

/** `dd/mm/aaaa` a partir de uma data ISO (`event_date`, sem hora). */
function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const [year, month, day] = iso.slice(0, 10).split("-");
  if (!year || !month || !day) return "—";
  return `${day}/${month}/${year}`;
}

/** `dd/mm/aaaa hh:mm` — a listagem antiga mostrava data E hora do recebimento. */
function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return `${date.toLocaleDateString("pt-BR")} ${date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}

// ══════════════════════════════════════════════════════════════════
//  Links públicos
// ══════════════════════════════════════════════════════════════════

interface PublicFormCardProps {
  nome: string;
  descricao: string;
  url: string;
  canEditStructure: boolean;
  onEditFields: () => void;
}

function PublicFormCard({ nome, descricao, url, canEditStructure, onEditFields }: PublicFormCardProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Clipboard bloqueado (contexto não seguro): o campo fica selecionado para Ctrl+C.
      return;
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">📋 {nome}</CardTitle>
        <p className="text-xs text-muted">{descricao}</p>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            readOnly
            value={url}
            aria-label={`Link do formulário ${nome}`}
            className="h-9 flex-1 text-xs"
            onClick={(e) => e.currentTarget.select()}
          />
          <div className="flex shrink-0 gap-2">
            <Button size="sm" variant="outline" onClick={copy}>
              {copied ? "✓ Copiado" : "Copiar link"}
            </Button>
            <Button size="sm" variant="ghost" asChild>
              <a href={url} target="_blank" rel="noopener noreferrer">
                Abrir
              </a>
            </Button>
          </div>
        </div>
        <p aria-live="polite" className="sr-only">
          {copied ? "Link copiado para a área de transferência." : ""}
        </p>
        {canEditStructure && (
          <button type="button" className="text-xs text-accent hover:underline" onClick={onEditFields}>
            ✎ Editar campos deste formulário
          </button>
        )}
      </CardContent>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Tabela de respostas
// ══════════════════════════════════════════════════════════════════

/** Badges coloridos de vínculo — verde quando resolvido, âmbar quando pendente. */
function SituacaoBadges({ response }: { response: FormResponseSummary }) {
  return (
    <div className="flex flex-wrap gap-1">
      {response.client_id ? (
        <MetricBadge tone="green">Cliente: {response.client_name ?? "vinculado"}</MetricBadge>
      ) : (
        <MetricBadge tone="gold">Sem cliente</MetricBadge>
      )}
      {response.event_id ? (
        <MetricBadge tone="green">Evento vinculado</MetricBadge>
      ) : (
        <MetricBadge tone="gold">Sem evento</MetricBadge>
      )}
    </div>
  );
}

function ResponsesTable({
  responses,
  onOpen,
}: {
  responses: FormResponseSummary[];
  onOpen: (id: number) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[880px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
            <th className="px-3 py-2 font-medium">Contratante</th>
            <th className="px-3 py-2 font-medium">Formulário</th>
            <th className="px-3 py-2 font-medium">Data do evento</th>
            <th className="px-3 py-2 font-medium">Recebida em</th>
            <th className="px-3 py-2 font-medium">Situação</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {responses.map((r) => (
            <tr key={r.id} className="border-b border-line last:border-0 hover:bg-surface-2">
              <td className="px-3 py-2">
                <button
                  type="button"
                  className="text-left font-medium text-ink hover:text-accent hover:underline"
                  onClick={() => onOpen(r.id)}
                >
                  {r.contact_name}
                </button>
                {r.contact_phone_display && (
                  <p className="text-xs text-muted">{r.contact_phone_display}</p>
                )}
              </td>
              <td className="whitespace-nowrap px-3 py-2">
                <MetricBadge tone="neutral">{r.form_type_label}</MetricBadge>
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-ink">{formatDate(r.event_date)}</td>
              <td className="whitespace-nowrap px-3 py-2 text-muted">{formatDateTime(r.created_at)}</td>
              <td className="px-3 py-2">
                <SituacaoBadges response={r} />
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                <Button size="sm" variant="ghost" onClick={() => onOpen(r.id)}>
                  Ver
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Detalhe da resposta (Dialog)
// ══════════════════════════════════════════════════════════════════

function ClienteSection({ id }: { id: number }) {
  const detalhe = useFormResponseDetail(id);
  const associate = useAssociateClient(id);
  const dissociate = useDissociateClient(id);
  const [clientQuery, setClientQuery] = useState("");
  const clientSearch = useClientSearch(clientQuery);

  const response = detalhe.data?.response;
  const suggested = detalhe.data?.suggested_client ?? null;
  if (!response) return null;

  if (response.client_id) {
    return (
      <div className="flex items-center justify-between gap-2">
        <MetricBadge tone="green" size="sm">
          Cliente: {response.client_name ?? "vinculado"}
        </MetricBadge>
        <Button size="sm" variant="ghost" loading={dissociate.isPending} onClick={() => dissociate.mutate()}>
          Desassociar
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <MetricBadge tone="gold" size="sm">
        Sem cliente
      </MetricBadge>

      {suggested && (
        <Button size="sm" loading={associate.isPending} onClick={() => associate.mutate(suggested.id)}>
          Associar ao cliente sugerido: {suggested.name}
        </Button>
      )}

      <div>
        <Input
          className="h-9"
          placeholder="Buscar cliente por nome ou telefone…"
          value={clientQuery}
          onChange={(e) => setClientQuery(e.target.value)}
        />
        {clientSearch.data && clientSearch.data.length > 0 && (
          <ul className="mt-1 max-h-40 overflow-y-auto rounded-md border border-line">
            {clientSearch.data.map((c) => {
              // `associate.variables` guarda o argumento da mutation em curso: só a linha
              // realmente clicada mostra "Associando…" (Princípio V — nenhum botão morto).
              const associatingThis = associate.isPending && associate.variables === c.id;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    disabled={associate.isPending}
                    aria-busy={associatingThis}
                    className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm text-ink hover:bg-surface-2 disabled:opacity-60"
                    onClick={() => associate.mutate(c.id)}
                  >
                    <span className="min-w-0 truncate">
                      {c.name} <span className="text-xs text-muted">{c.phone_display}</span>
                    </span>
                    {associatingThis && <span className="shrink-0 text-xs text-muted">Associando…</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {clientQuery.trim().length >= 2 && clientSearch.data?.length === 0 && (
          <p className="mt-1 text-xs text-muted">Nenhum cliente encontrado com esse termo.</p>
        )}
      </div>

      {/* Criação inline: `POST /respostas/<id>/associar` sem `client_id` reaproveita o cliente
          existente quando o telefone bate (mesma regra do `quick-create`) e ainda preenche
          CPF/CNPJ/endereço a partir da resposta — por isso não chamamos `/clientes/quick-create`
          direto, que faria só metade do trabalho e duplicaria a regra. */}
      <Button
        size="sm"
        variant="outline"
        loading={associate.isPending}
        disabled={!response.contact_phone_display}
        onClick={() => associate.mutate(undefined)}
      >
        Criar cliente com os dados desta resposta
      </Button>
      {!response.contact_phone_display && (
        <p className="text-xs text-muted">
          A resposta não tem telefone válido — associe a um cliente existente.
        </p>
      )}
      {associate.isError && (
        <p className="text-sm text-red">Não foi possível associar o cliente. Tente novamente.</p>
      )}
    </div>
  );
}

function EventoSection({ id, onPrefillEvent }: { id: number; onPrefillEvent: () => void }) {
  const detalhe = useFormResponseDetail(id);
  const linkEvent = useLinkEvent(id);
  const unlinkEvent = useUnlinkEvent(id);
  const response = detalhe.data?.response;
  const [eventDate, setEventDate] = useState("");

  const effectiveDate = eventDate || response?.event_date || "";
  const eventos = useGastosEventos(effectiveDate);

  if (!response) return null;

  if (response.event_id) {
    return (
      <div className="flex items-center justify-between gap-2">
        <MetricBadge tone="green" size="sm">
          {response.event_title ?? "Evento vinculado"}
        </MetricBadge>
        <Button size="sm" variant="ghost" loading={unlinkEvent.isPending} onClick={() => unlinkEvent.mutate()}>
          Desvincular
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <MetricBadge tone="gold" size="sm">
        Sem evento
      </MetricBadge>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="date"
          aria-label="Data para buscar eventos"
          className={`${CONTROL} h-9 sm:w-44`}
          value={effectiveDate}
          onChange={(e) => setEventDate(e.target.value)}
        />
        {/* O `select` É o disparador da ação aqui — enquanto o vínculo está em voo ele trava e
            anuncia "Vinculando…" no próprio rótulo (Princípio V vale para qualquer controle que
            dispara mutation, não só para `Button`). */}
        <select
          aria-label="Evento da agenda"
          className={`${CONTROL} h-9 flex-1 disabled:cursor-not-allowed disabled:opacity-60`}
          value=""
          disabled={!effectiveDate || eventos.isLoading || linkEvent.isPending}
          aria-busy={linkEvent.isPending}
          onChange={(e) => e.target.value && linkEvent.mutate(Number(e.target.value))}
        >
          <option value="">
            {linkEvent.isPending
              ? "Vinculando…"
              : !effectiveDate
                ? "Escolha uma data primeiro…"
                : eventos.isLoading
                  ? "Carregando eventos…"
                  : eventos.isError
                    ? "Erro ao buscar eventos"
                    : "Selecione o evento…"}
          </option>
          {eventos.data?.events.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.label}
            </option>
          ))}
        </select>
      </div>
      {effectiveDate && eventos.isError && (
        <p className="text-xs text-red">
          Não foi possível buscar os eventos dessa data.{" "}
          <button type="button" className="underline" onClick={() => eventos.refetch()}>
            Tentar novamente
          </button>
        </p>
      )}
      {effectiveDate && !eventos.isLoading && !eventos.isError && eventos.data?.events.length === 0 && (
        <p className="text-xs text-muted">Nenhum evento nessa data.</p>
      )}
      <Button size="sm" variant="outline" onClick={onPrefillEvent}>
        Criar evento com os dados desta resposta
      </Button>
      {linkEvent.isError && (
        <p className="text-sm text-red">Não foi possível vincular o evento. Tente novamente.</p>
      )}
    </div>
  );
}

function ResponseDetailDialog({
  id,
  open,
  onClose,
}: {
  id: number | null;
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const detalhe = useFormResponseDetail(id);
  const del = useDeleteFormResponse();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const response = detalhe.data?.response;
  const canEditStructure = detalhe.data?.can_edit_structure ?? false;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setConfirmingDelete(false);
          onClose();
        }
      }}
    >
      <DialogContent open={open} className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{response?.contact_name ?? "Resposta do formulário"}</DialogTitle>
          <DialogDescription>
            {response
              ? `${response.form_type_label} · ${response.contact_phone_display || "sem telefone"} · recebida em ${formatDateTime(response.created_at)}`
              : "Carregando…"}
          </DialogDescription>
        </DialogHeader>

        {detalhe.isLoading && <Skeleton className="h-48 w-full" />}

        {detalhe.isError && (
          <div className="text-sm text-muted">
            Não foi possível carregar esta resposta.{" "}
            <button type="button" className="text-accent hover:underline" onClick={() => detalhe.refetch()}>
              Tentar novamente
            </button>
          </div>
        )}

        {response && id != null && (
          <div className="space-y-4">
            <div className="space-y-3">
              {response.data_sections.map((section) => (
                <div key={section.secao}>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
                    {section.secao}
                  </p>
                  <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-2">
                    {section.campos.map(([, label, value]) => (
                      <div key={label} className="min-w-0">
                        <dt className="text-xs text-muted">{label}</dt>
                        <dd className="break-words text-sm text-ink">{value || "—"}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ))}
            </div>

            <div className="border-t border-line pt-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Cliente</p>
              <ClienteSection id={id} />
            </div>

            <div className="border-t border-line pt-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Evento</p>
              <EventoSection
                id={id}
                onPrefillEvent={() => navigate(`/events/new?form_response_id=${id}`)}
              />
            </div>

            {canEditStructure && (
              <DialogFooter className="border-t border-line pt-3 sm:justify-between">
                {confirmingDelete ? (
                  <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-sm text-ink">Excluir esta resposta? A ação não pode ser desfeita.</p>
                    <div className="flex gap-2">
                      <Button size="sm" variant="ghost" onClick={() => setConfirmingDelete(false)}>
                        Cancelar
                      </Button>
                      <Button
                        size="sm"
                        loading={del.isPending}
                        onClick={() => del.mutate(id, { onSuccess: onClose })}
                      >
                        Excluir
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button size="sm" variant="ghost" onClick={() => setConfirmingDelete(true)}>
                    Excluir resposta
                  </Button>
                )}
              </DialogFooter>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Editor de estrutura (Dialog, SUPERADMIN)
// ══════════════════════════════════════════════════════════════════

function FieldEditorDialog({
  formType,
  onClose,
  onChangeFormType,
}: {
  formType: FormType | null;
  onClose: () => void;
  onChangeFormType: (next: FormType) => void;
}) {
  const open = formType !== null;
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent open={open} className="max-h-[85vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editor de campos</DialogTitle>
          <DialogDescription>
            Alterações valem imediatamente para quem abrir o formulário público.
          </DialogDescription>
        </DialogHeader>

        {formType && (
          <>
            <Tabs value={formType} onValueChange={(v) => onChangeFormType(v as FormType)}>
              <TabsList>
                <TabsTrigger value="comum">Pré-contrato</TabsTrigger>
                <TabsTrigger value="corporativo">Corporativo</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="mt-4">
              <FormFieldEditor formType={formType} />
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════
//  Página
// ══════════════════════════════════════════════════════════════════

export function FormulariosAdminPage() {
  const reduceMotion = useReducedMotion();
  const currentUser = useCurrentUser();
  const canEditStructure = currentUser.data?.is_superadmin ?? false;

  const [q, setQ] = useState("");
  const [formFilter, setFormFilter] = useState<FormFilter>("todos");
  const [selected, setSelected] = useState<number | null>(null);
  const [editorFormType, setEditorFormType] = useState<FormType | null>(null);

  const isSearching = q.trim().length >= 2;
  const list = useFormResponses();
  const search = useSearchFormResponses(q);
  const source = isSearching ? search : list;

  const responses = useMemo(() => {
    const all = source.data?.responses ?? [];
    return formFilter === "todos" ? all : all.filter((r) => r.form_type === formFilter);
  }, [source.data, formFilter]);

  return (
    <div className="mx-auto max-w-6xl space-y-5 p-4 sm:p-6">
      <PageHeader
        title="Formulários"
        subtitle="Copie o link, envie para a cliente e acompanhe as respostas aqui"
        className="mb-0"
        actions={
          canEditStructure ? (
            <Button variant="outline" size="sm" onClick={() => setEditorFormType("comum")}>
              ✎ Editor de campos
            </Button>
          ) : undefined
        }
      />

      {/* ── Links públicos ───────────────────────────────────────────── */}
      <div className="grid gap-3 md:grid-cols-2">
        {PUBLIC_FORMS.map((form) => (
          <PublicFormCard
            key={form.slug}
            nome={form.nome}
            descricao={form.descricao}
            url={publicFormUrl(form.slug)}
            canEditStructure={canEditStructure}
            onEditFields={() => setEditorFormType(form.formType)}
          />
        ))}
      </div>

      {/* ── Respostas ────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Respostas recebidas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <Input
              className="h-9 sm:max-w-sm"
              placeholder="Buscar por nome do contratante ou telefone…"
              aria-label="Buscar respostas"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Tabs value={formFilter} onValueChange={(v) => setFormFilter(v as FormFilter)}>
              <TabsList>
                <TabsTrigger value="todos">Todos</TabsTrigger>
                <TabsTrigger value="comum">Pré-contrato</TabsTrigger>
                <TabsTrigger value="corporativo">Corporativo</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {source.isLoading && (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          )}

          {source.isError && (
            <p className="text-sm text-muted">
              Não foi possível carregar as respostas.{" "}
              <button type="button" className="text-accent hover:underline" onClick={() => source.refetch()}>
                Tentar novamente
              </button>
            </p>
          )}

          {!source.isLoading && !source.isError && responses.length === 0 && (
            <p className="text-sm text-muted">
              {isSearching || formFilter !== "todos"
                ? "Nenhuma resposta encontrada com esses filtros."
                : "Nenhuma resposta ainda. Envie o link de um formulário para uma cliente — as respostas aparecem aqui assim que ela enviar."}
            </p>
          )}

          {!source.isLoading && responses.length > 0 && (
            <motion.div
              initial={reduceMotion ? undefined : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
            >
              <ResponsesTable responses={responses} onOpen={setSelected} />
            </motion.div>
          )}
        </CardContent>
      </Card>

      <ResponseDetailDialog id={selected} open={selected !== null} onClose={() => setSelected(null)} />

      {canEditStructure && (
        <FieldEditorDialog
          formType={editorFormType}
          onClose={() => setEditorFormType(null)}
          onChangeFormType={setEditorFormType}
        />
      )}
    </div>
  );
}
