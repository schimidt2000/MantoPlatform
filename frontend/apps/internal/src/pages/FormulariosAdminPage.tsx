import { useState } from "react";
import { Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Skeleton } from "@manto/ui";
import { useClientSearch } from "../lib/clientes";
import { useGastosEventos } from "../lib/gastos";
import {
  useAssociateClient,
  useCreateField,
  useDeleteField,
  useDeleteFormResponse,
  useDissociateClient,
  useFormFieldDefinitions,
  useFormResponseDetail,
  useFormResponses,
  useLinkEvent,
  useMoveField,
  useSearchFormResponses,
  useUnlinkEvent,
  useUpdateField,
  type FormResponseSummary,
} from "../lib/formulariosAdmin";

const INPUT = "h-9 rounded-md border border-line bg-panel px-2 text-sm text-ink";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

function ResponseDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const detalhe = useFormResponseDetail(id);
  const associate = useAssociateClient(id);
  const dissociate = useDissociateClient(id);
  const linkEvent = useLinkEvent(id);
  const unlinkEvent = useUnlinkEvent(id);
  const del = useDeleteFormResponse();

  const [clientQuery, setClientQuery] = useState("");
  const [eventDate, setEventDate] = useState("");
  const clientSearch = useClientSearch(clientQuery);
  const eventos = useGastosEventos(eventDate);

  if (detalhe.isLoading) return <Skeleton className="h-48 w-full" />;
  if (!detalhe.data) return null;

  const { response, suggested_client, can_edit_structure } = detalhe.data;

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="font-medium text-ink">{response.contact_name}</p>
            <p className="text-xs text-muted">
              {response.form_type_label} · {response.contact_phone_display} · {formatDate(response.created_at)}
            </p>
          </div>
          <Button size="sm" variant="ghost" onClick={onClose}>
            Fechar
          </Button>
        </div>

        <div className="space-y-1">
          {response.data_sections.map((section) => (
            <div key={section.secao}>
              <p className="text-xs font-medium text-muted">{section.secao}</p>
              {section.campos.map(([, label, value]) => (
                <p key={label} className="text-sm text-ink">
                  <span className="text-muted">{label}:</span> {value || "—"}
                </p>
              ))}
            </div>
          ))}
        </div>

        <div className="space-y-2 border-t border-line pt-2">
          <p className="text-xs font-medium text-muted">Cliente</p>
          {response.client_name ? (
            <div className="flex items-center justify-between text-sm">
              <span className="text-ink">{response.client_name}</span>
              <Button size="sm" variant="ghost" loading={dissociate.isPending} onClick={() => dissociate.mutate()}>
                Desassociar
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {suggested_client && (
                <Button
                  size="sm"
                  loading={associate.isPending}
                  onClick={() => associate.mutate(suggested_client.id)}
                >
                  Associar sugerido: {suggested_client.name}
                </Button>
              )}
              <div className="flex gap-2">
                <input
                  className={INPUT}
                  placeholder="Buscar cliente…"
                  value={clientQuery}
                  onChange={(e) => setClientQuery(e.target.value)}
                />
                <Button size="sm" onClick={() => associate.mutate(undefined)} loading={associate.isPending}>
                  Criar novo
                </Button>
              </div>
              {clientSearch.data && clientSearch.data.length > 0 && (
                <div className="space-y-1">
                  {clientSearch.data.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      className="block text-sm text-accent hover:underline"
                      onClick={() => associate.mutate(c.id)}
                    >
                      {c.name} — {c.phone_display}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-2 border-t border-line pt-2">
          <p className="text-xs font-medium text-muted">Evento</p>
          {response.event_title ? (
            <div className="flex items-center justify-between text-sm">
              <span className="text-ink">{response.event_title}</span>
              <Button size="sm" variant="ghost" loading={unlinkEvent.isPending} onClick={() => unlinkEvent.mutate()}>
                Desvincular
              </Button>
            </div>
          ) : (
            <div className="flex gap-2">
              <input
                type="date"
                className={INPUT}
                value={eventDate || response.event_date || ""}
                onChange={(e) => setEventDate(e.target.value)}
              />
              <select
                className={INPUT}
                onChange={(e) => e.target.value && linkEvent.mutate(Number(e.target.value))}
                value=""
              >
                <option value="">Selecione o evento…</option>
                {eventos.data?.events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.label}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {can_edit_structure && (
          <Button
            size="sm"
            variant="ghost"
            loading={del.isPending}
            onClick={() => {
              if (window.confirm("Excluir esta resposta?")) del.mutate(id, { onSuccess: onClose });
            }}
          >
            Excluir resposta
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function FieldEditor({ formType }: { formType: "comum" | "corporativo" }) {
  const fields = useFormFieldDefinitions(formType);
  const create = useCreateField(formType);
  const update = useUpdateField(formType);
  const move = useMoveField(formType);
  const del = useDeleteField(formType);

  const [label, setLabel] = useState("");
  const [sectionName, setSectionName] = useState("");
  const [fieldType, setFieldType] = useState("texto_curto");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Editor de campos — {formType}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {fields.data?.fields.map((f) => (
          <div key={f.id} className="flex items-center justify-between gap-2 border-b border-line py-2 last:border-0">
            <div className="min-w-0">
              <p className="truncate text-sm text-ink">
                {f.label} <span className="text-xs text-muted">({f.field_type})</span>
              </p>
              <p className="text-xs text-muted">{f.section_name}</p>
            </div>
            <div className="flex shrink-0 gap-1">
              <Button size="sm" variant="ghost" onClick={() => move.mutate({ id: f.id, direction: "up" })}>
                ↑
              </Button>
              <Button size="sm" variant="ghost" onClick={() => move.mutate({ id: f.id, direction: "down" })}>
                ↓
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  const novoLabel = window.prompt("Novo rótulo:", f.label);
                  if (novoLabel) update.mutate({ id: f.id, label: novoLabel, required: f.required });
                }}
              >
                Editar
              </Button>
              {!f.is_system && (
                <Button
                  size="sm"
                  variant="ghost"
                  loading={del.isPending}
                  onClick={() => {
                    if (window.confirm(`Excluir o campo "${f.label}"?`)) del.mutate(f.id);
                  }}
                >
                  Excluir
                </Button>
              )}
            </div>
          </div>
        ))}
        <div className="flex flex-wrap gap-2 pt-2">
          <input className={INPUT} placeholder="Rótulo" value={label} onChange={(e) => setLabel(e.target.value)} />
          <input
            className={INPUT}
            placeholder="Seção"
            value={sectionName}
            onChange={(e) => setSectionName(e.target.value)}
          />
          <select className={INPUT} value={fieldType} onChange={(e) => setFieldType(e.target.value)}>
            <option value="texto_curto">Texto curto</option>
            <option value="texto_longo">Texto longo</option>
            <option value="selecao">Seleção</option>
            <option value="data">Data</option>
            <option value="hora">Hora</option>
            <option value="telefone">Telefone</option>
            <option value="email">E-mail</option>
            <option value="cpf">CPF</option>
            <option value="cnpj">CNPJ</option>
            <option value="cep">CEP</option>
            <option value="sim_nao">Sim/Não</option>
          </select>
          <Button
            size="sm"
            loading={create.isPending}
            onClick={() => {
              if (!label.trim() || !sectionName.trim()) return;
              create.mutate(
                { label, section_name: sectionName, field_type: fieldType },
                { onSuccess: () => { setLabel(""); setSectionName(""); } },
              );
            }}
          >
            Adicionar campo
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function FormulariosAdminPage() {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [showEditor, setShowEditor] = useState<"comum" | "corporativo" | null>(null);

  const list = useFormResponses();
  const search = useSearchFormResponses(q);
  const responses: FormResponseSummary[] = q.trim().length >= 2 ? search.data?.responses ?? [] : list.data?.responses ?? [];
  const isLoading = q.trim().length >= 2 ? search.isLoading : list.isLoading;

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Formulários"
        subtitle="Respostas de pré-contrato e corporativo"
        className="mb-0"
        actions={
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setShowEditor("comum")}>
              Editor (comum)
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowEditor("corporativo")}>
              Editor (corporativo)
            </Button>
          </div>
        }
      />

      {showEditor && (
        <div>
          <Button size="sm" variant="ghost" onClick={() => setShowEditor(null)}>
            ‹ Voltar à lista
          </Button>
          <FieldEditor formType={showEditor} />
        </div>
      )}

      {!showEditor && (
        <>
          <input
            className="h-10 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink"
            placeholder="Buscar por nome ou telefone…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />

          {isLoading && (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}

          {!isLoading && responses.length === 0 && <p className="text-sm text-muted">Nenhuma resposta encontrada.</p>}

          <div className="space-y-2">
            {responses.map((r) => (
              <div key={r.id}>
                <Card>
                  <CardContent className="flex items-center justify-between gap-3 p-3">
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => setSelected(selected === r.id ? null : r.id)}
                    >
                      <p className="truncate font-medium text-ink">{r.contact_name}</p>
                      <p className="text-xs text-muted">
                        {r.form_type_label} · {r.contact_phone_display} · {formatDate(r.created_at)}
                      </p>
                    </button>
                    <div className="text-right text-xs text-muted">
                      {r.client_id ? "Com cliente" : "Sem cliente"} · {r.event_id ? "Com evento" : "Sem evento"}
                    </div>
                  </CardContent>
                </Card>
                {selected === r.id && <ResponseDetail id={r.id} onClose={() => setSelected(null)} />}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
