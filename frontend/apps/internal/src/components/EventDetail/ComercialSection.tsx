import { useState } from "react";
import { Link } from "react-router-dom";
import { Pencil } from "lucide-react";
import { Badge, Button } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { MoneyInput } from "@manto/money";
import type { EventoDetalhe } from "../../lib/agenda";
import { useEventCreateOptions } from "../../lib/eventCreate";
import {
  useSetEventClients,
  useSetEventFormResponse,
  useUpdateEventComercial,
  type EventComercialInput,
} from "../../lib/eventInline";
import {
  useDesagruparEvento,
  useRemoverSatelite,
  useRenomearGrupo,
} from "../../lib/eventOps";
import { ClientPicker, type SelectedClient } from "../ClientPicker";
import { FormResponsePicker, type SelectedFormResponse } from "../FormResponsePicker";
import { AgruparEventosDialog } from "./AgruparEventosDialog";
import { ColecoesComerciaisPanel } from "./ColecoesComerciaisPanel";
import { brl, DataRow, Empty, formatDay, INPUT_CLASS, Panel } from "./parts";

/** Rótulos legíveis das formas de pagamento gravadas no evento. */
const PAYMENT_METHOD_LABELS: Record<string, string> = {
  avista: "À vista (PIX)",
  pix_parcelado: "Dividido no PIX",
  faturado: "Faturado",
  cartao: "Cartão de crédito",
  futuro: "Pagamento futuro",
  parcelado: "Parcelado (datas)",
};

const LABEL_CLASS = "mb-1 block text-[11px] font-bold uppercase tracking-wider text-muted";
const MONEY_CLASS = "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

/** Um card da grade de resultado. `emphasis` destaca o lucro líquido. */
function KpiCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone: "neutral" | "green" | "red";
}) {
  const toneClass =
    tone === "green" ? "text-green" : tone === "red" ? "text-red" : "text-ink";
  return (
    <div className="rounded-md border border-line bg-surface-2/60 p-3">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-0.5 text-lg font-semibold tabular-nums ${toneClass}`}>{value}</div>
      {hint && <div className="text-[11px] text-muted">{hint}</div>}
    </div>
  );
}

/**
 * Grade financeira de resultado do evento (feature 190): venda, custo de cachês, gastos
 * extras, comissão e o lucro líquido em destaque — verde quando positivo, vermelho quando
 * negativo. Os números vêm prontos do servidor (`kpi`), agregados pelo grupo comercial.
 */
function KpiGrid({ data }: { data: EventoDetalhe }) {
  const kpi = data.kpi;
  if (!kpi) return null;
  const gastos = data.gastos ?? [];
  const lucro = kpi.lucro ?? 0;

  return (
    <Panel
      title={`Resultado${kpi.group_size > 1 ? ` — grupo de ${kpi.group_size} eventos` : ""}`}
    >
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
        <KpiCard label="Venda" value={brl(kpi.sale_value)} tone="neutral" />
        <KpiCard label="Custo (cachês)" value={brl(kpi.cost)} tone="neutral" />
        <KpiCard
          label="Gastos extras"
          value={brl(kpi.expenses_total)}
          hint={gastos.length ? `${gastos.length} aprovado(s)` : undefined}
          tone="neutral"
        />
        {/* O percentual só descreve o número quando ele é estimativa. Vindo da linha real, a
            conta pode não ser "% sobre a venda" (EducaManto incide sobre o lucro) — estampar
            "Comissão (2,5%)" ali seria uma conta que não fecha. */}
        <KpiCard
          label={kpi.commission_source === "linha" ? "Comissão" : `Comissão (${kpi.rate}%)`}
          value={brl(kpi.commission)}
          hint={
            kpi.commission_source === "linha"
              ? (kpi.seller ?? undefined)
              : [kpi.seller, "estimativa — ainda sem lançamento"].filter(Boolean).join(" · ")
          }
          tone="neutral"
        />
        <KpiCard
          label="Lucro líquido"
          value={brl(lucro)}
          hint="venda − cachês − gastos"
          tone={lucro < 0 ? "red" : "green"}
        />
      </div>

      {gastos.length > 0 && (
        <div className="mt-3">
          <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-muted">
            Gastos extras vinculados (aprovados)
          </div>
          <ul className="divide-y divide-line text-sm">
            {gastos.map((gasto) => (
              <li key={gasto.id} className="flex items-center justify-between gap-2 py-1.5">
                <span className="min-w-0 truncate text-ink">
                  {gasto.description}
                  <span className="ml-2 text-xs text-muted">{gasto.category}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="text-xs text-muted tabular-nums">
                    {formatDay(gasto.expense_date)}
                  </span>
                  <span className="tabular-nums text-ink">{brl(gasto.amount)}</span>
                  {gasto.receipt_path && (
                    <a
                      href={assetUrl(gasto.receipt_path)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue underline"
                    >
                      Ver
                    </a>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

/**
 * Formulário dos valores da venda, aberto no lugar da leitura (feature 215).
 *
 * Grava por `PATCH /events/<id>/comercial` — recorte estreito que não encosta em elenco nem
 * em clientes (que têm o seu próprio painel logo acima). Cortesia/permuta zera a venda no
 * servidor, então o formulário esconde os valores quando ela está marcada.
 */
function VendaForm({ data, onClose }: { data: EventoDetalhe; onClose: () => void }) {
  const venda = data.venda!;
  const salvar = useUpdateEventComercial(data.event.id);
  const options = useEventCreateOptions();
  const [form, setForm] = useState<EventComercialInput>(() => ({
    sale_value: venda.sale_value,
    sale_value_gross: venda.sale_value_gross,
    transport_value: venda.transport_value,
    with_invoice: venda.with_invoice,
    is_cortesia_permuta: venda.is_cortesia_permuta,
    seller_id: venda.seller_id,
    sale_date: venda.sale_date ? venda.sale_date.slice(0, 10) : null,
    commission_rate: venda.commission_rate,
    payment_method: venda.payment_method,
    payment_installments: venda.payment_installments,
    payment_due_date: venda.payment_due_date ? venda.payment_due_date.slice(0, 10) : null,
  }));

  const set = <K extends keyof EventComercialInput>(key: K, value: EventComercialInput[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          className="h-5 w-5"
          checked={form.is_cortesia_permuta}
          onChange={(e) => set("is_cortesia_permuta", e.target.checked)}
        />
        Cortesia / permuta (zera o valor de venda)
      </label>

      {!form.is_cortesia_permuta && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className={LABEL_CLASS}>Valor antes do desconto</label>
            <MoneyInput
              className={MONEY_CLASS}
              value={form.sale_value_gross ?? 0}
              onValueChange={(v) => set("sale_value_gross", v)}
              aria-label="Valor antes do desconto"
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Valor de venda final</label>
            <MoneyInput
              className={MONEY_CLASS}
              value={form.sale_value ?? 0}
              onValueChange={(v) => set("sale_value", v)}
              aria-label="Valor de venda final"
            />
          </div>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL_CLASS}>Transporte</label>
          <MoneyInput
            className={MONEY_CLASS}
            value={form.transport_value ?? 0}
            onValueChange={(v) => set("transport_value", v)}
            aria-label="Valor de transporte"
          />
        </div>
        <div>
          <label className={LABEL_CLASS} htmlFor="venda-comissao">
            Taxa de comissão (%)
          </label>
          <input
            id="venda-comissao"
            type="number"
            step="0.1"
            min="0"
            className={INPUT_CLASS}
            value={form.commission_rate ?? ""}
            placeholder="padrão do sistema"
            onChange={(e) =>
              set("commission_rate", e.target.value === "" ? null : Number(e.target.value))
            }
          />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL_CLASS} htmlFor="venda-forma">
            Forma de pagamento
          </label>
          <select
            id="venda-forma"
            className={INPUT_CLASS}
            value={form.payment_method ?? ""}
            onChange={(e) => set("payment_method", e.target.value || null)}
          >
            <option value="">— Selecionar —</option>
            {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={LABEL_CLASS} htmlFor="venda-parcelas">
            Parcelas
          </label>
          <input
            id="venda-parcelas"
            type="number"
            min="1"
            className={INPUT_CLASS}
            value={form.payment_installments ?? ""}
            onChange={(e) =>
              set("payment_installments", e.target.value === "" ? null : Number(e.target.value))
            }
          />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL_CLASS} htmlFor="venda-data">
            Data da venda
          </label>
          <input
            id="venda-data"
            type="date"
            className={INPUT_CLASS}
            value={form.sale_date ?? ""}
            onChange={(e) => set("sale_date", e.target.value || null)}
          />
        </div>
        <div>
          <label className={LABEL_CLASS} htmlFor="venda-vencimento">
            Vencimento do pagamento
          </label>
          <input
            id="venda-vencimento"
            type="date"
            className={INPUT_CLASS}
            value={form.payment_due_date ?? ""}
            onChange={(e) => set("payment_due_date", e.target.value || null)}
          />
        </div>
      </div>

      <div>
        <label className={LABEL_CLASS} htmlFor="venda-vendedor">
          Vendedor responsável
        </label>
        <select
          id="venda-vendedor"
          className={INPUT_CLASS}
          value={form.seller_id ?? ""}
          onChange={(e) => set("seller_id", e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">— sem vendedor —</option>
          {(options.data?.sellers ?? []).map((seller) => (
            <option key={seller.id} value={seller.id}>
              {seller.name}
            </option>
          ))}
        </select>
      </div>

      <label className="flex items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          className="h-5 w-5"
          checked={form.with_invoice}
          onChange={(e) => set("with_invoice", e.target.checked)}
        />
        Cliente solicitou nota fiscal
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          loading={salvar.isPending}
          onClick={() => salvar.mutate(form, { onSuccess: onClose })}
        >
          Salvar venda
        </Button>
        <Button variant="ghost" onClick={onClose} disabled={salvar.isPending}>
          Cancelar
        </Button>
        {salvar.isError && <span className="text-sm text-red">{salvar.error?.message}</span>}
      </div>
    </div>
  );
}

/**
 * Painel de clientes do evento (feature 215) — vinculação editada onde é exibida.
 *
 * `PUT /events/<id>/clients` recebe a lista inteira: a tela mantém o rascunho local enquanto
 * o usuário mexe e só grava no "Salvar clientes", para não disparar uma escrita por tecla.
 */
function ClientesPanel({ data }: { data: EventoDetalhe }) {
  const venda = data.venda!;
  const salvar = useSetEventClients(data.event.id);
  const options = useEventCreateOptions();
  const [editando, setEditando] = useState(false);
  const [clientes, setClientes] = useState<SelectedClient[]>([]);
  const canEdit = Boolean(data.flags.can_edit_core);

  const abrir = () => {
    setClientes(
      venda.clients.map((c) => ({
        client_id: c.client_id,
        name: c.name ?? "—",
        relation: c.relation,
      })),
    );
    setEditando(true);
  };

  return (
    <Panel
      title="Clientes"
      actions={
        canEdit && !editando ? (
          <Button variant="outline" size="sm" onClick={abrir}>
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Editar
          </Button>
        ) : null
      }
    >
      {editando ? (
        <div className="space-y-3">
          <ClientPicker
            value={clientes}
            onChange={setClientes}
            relationOptions={options.data?.client_relation_tipos ?? []}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button
              loading={salvar.isPending}
              onClick={() =>
                salvar.mutate(
                  {
                    clients: clientes.map((c) => ({
                      client_id: c.client_id,
                      relation: c.relation,
                    })),
                  },
                  { onSuccess: () => setEditando(false) },
                )
              }
            >
              Salvar clientes
            </Button>
            <Button variant="ghost" onClick={() => setEditando(false)} disabled={salvar.isPending}>
              Cancelar
            </Button>
            {salvar.isError && <span className="text-sm text-red">{salvar.error?.message}</span>}
          </div>
        </div>
      ) : venda.clients.length === 0 ? (
        <Empty>Nenhum cliente associado.</Empty>
      ) : (
        <ul className="space-y-1">
          {venda.clients.map((client) => (
            <li
              key={client.client_id}
              className="flex items-center justify-between gap-2 rounded-md border border-line bg-surface-2/60 px-2 py-1.5 text-sm"
            >
              {/* Sem nome cadastrado a linha continua texto: um link chamado "—" não diz
                  para onde vai (e é um alvo sem nome acessível). */}
              {client.name ? (
                <Link
                  to={`/clientes/${client.client_id}`}
                  className="truncate text-ink hover:underline"
                >
                  {client.name}
                </Link>
              ) : (
                <span className="truncate text-ink">—</span>
              )}
              <Badge>{client.relation}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** Pré-contrato vinculado (feature 215) — vincular/desvincular sem sair da aba. */
function PreContratoPanel({ data }: { data: EventoDetalhe }) {
  const venda = data.venda!;
  const salvar = useSetEventFormResponse(data.event.id);
  const canEdit = Boolean(data.flags.can_edit_core);
  const atual = venda.form_response;

  if (!canEdit) {
    return (
      <Panel title="Pré-contrato">
        {atual ? (
          <DataRow label={atual.form_type}>
            <Link to={`/formularios?resposta=${atual.id}`} className="text-blue underline">
              {atual.name}
            </Link>
          </DataRow>
        ) : (
          <Empty>Nenhum pré-contrato vinculado.</Empty>
        )}
      </Panel>
    );
  }

  const selecionado: SelectedFormResponse | null = atual
    ? { id: atual.id, name: atual.name, form_type: atual.form_type }
    : null;

  return (
    <Panel title="Pré-contrato">
      <FormResponsePicker
        value={selecionado}
        onChange={(next) => salvar.mutate({ form_response_id: next ? next.id : null })}
      />
      {/* O picker desenha nome e tipo, mas não leva a lugar nenhum — e é ele que a maioria
          do comercial vê (o DataRow acima só aparece sem permissão de edição). */}
      {atual && (
        <Link
          to={`/formularios?resposta=${atual.id}`}
          className="mt-1 inline-block text-sm text-blue underline"
        >
          Ver resposta completa
        </Link>
      )}
      {salvar.isPending && <p className="mt-1 text-sm text-muted">Salvando…</p>}
      {salvar.isError && <p className="mt-1 text-sm text-red">{salvar.error?.message}</p>}
    </Panel>
  );
}

/** Dados da venda: valores, acréscimos e responsável (leitura + edição inline). */
function VendaPanel({ data }: { data: EventoDetalhe }) {
  const venda = data.venda;
  const [editando, setEditando] = useState(false);
  if (!venda) return null;
  const bruto = venda.sale_value_gross ?? 0;
  const liquido = venda.sale_value ?? 0;
  const desconto = bruto > liquido ? bruto - liquido : 0;
  // Satélite não edita venda: o dinheiro do contrato mora no principal, e o servidor recusa o
  // PATCH com 409. Sem esta trava o botão existia, a pessoa preenchia e só descobria no envio.
  const canEdit = Boolean(data.flags.can_edit_core) && !data.event.is_satellite;

  if (editando) {
    return (
      <Panel title="Comercial — dados da venda">
        <VendaForm data={data} onClose={() => setEditando(false)} />
      </Panel>
    );
  }

  return (
    <Panel
      title="Comercial — dados da venda"
      actions={
        canEdit ? (
          <Button variant="outline" size="sm" onClick={() => setEditando(true)}>
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Editar
          </Button>
        ) : null
      }
    >
      <div className="divide-y divide-line">
        {bruto > 0 && <DataRow label="Valor antes do desconto">{brl(bruto)}</DataRow>}
        {desconto > 0 && (
          <DataRow label="Desconto">
            <span className="text-red">− {brl(desconto)}</span>
          </DataRow>
        )}
        <DataRow label="Valor de venda final">
          <span className="font-semibold tabular-nums">{brl(liquido)}</span>
        </DataRow>
        {venda.transport_value ? (
          <DataRow label="Transporte">{brl(venda.transport_value)}</DataRow>
        ) : null}
        {venda.payment_method && (
          <DataRow label="Forma de pagamento">
            {PAYMENT_METHOD_LABELS[venda.payment_method] ?? venda.payment_method}
            {venda.payment_installments ? ` — ${venda.payment_installments}x` : ""}
          </DataRow>
        )}
        {venda.sale_date && <DataRow label="Data da venda">{formatDay(venda.sale_date)}</DataRow>}
        {venda.seller && <DataRow label="Vendedor responsável">{venda.seller}</DataRow>}
        {venda.orcamento_history_id != null && (
          <DataRow label="Orçamento de origem">
            <Link to={`/orcamento/${venda.orcamento_history_id}`} className="text-blue underline">
              Abrir orçamento
            </Link>
          </DataRow>
        )}
        {venda.commission_rate != null && (
          <DataRow label="Taxa de comissão">{venda.commission_rate}%</DataRow>
        )}
        {venda.is_cortesia_permuta && (
          <DataRow label="Cortesia / permuta">
            <Badge tone="gold">Sim</Badge>
          </DataRow>
        )}
        {venda.with_invoice && (
          <DataRow label="Nota fiscal">
            <Badge tone="blue">Solicitada</Badge>
          </DataRow>
        )}
      </div>

      {/* Os acréscimos saíram daqui para o painel próprio logo abaixo (feature 253), que mostra a
          mesma lista e permite editar. Mantê-los nos dois lugares deixava a tela com dois blocos
          "Acréscimos" um sob o outro. */}
    </Panel>
  );
}

/**
 * Agrupamento comercial do evento (feature 246): satélite, principal ou avulso.
 *
 * Os três estados são excludentes e mostram coisas diferentes: o satélite precisa do caminho de
 * volta ao principal, o principal precisa da lista de satélites (com como tirar cada um), e o
 * avulso precisa só do convite para agrupar.
 */
function GrupoPanel({ data }: { data: EventoDetalhe }) {
  const grupo = data.event.group;
  const canGroup = Boolean(data.flags.can_group);
  const [agruparAberto, setAgruparAberto] = useState(false);
  const desagrupar = useDesagruparEvento(data.event.id);
  const removerSatelite = useRemoverSatelite(data.event.id);
  const renomear = useRenomearGrupo(data.event.id);
  const [editandoNome, setEditandoNome] = useState(false);
  const [nome, setNome] = useState(grupo?.group_name ?? "");

  // Backend sem o bloco (bundle novo + API antiga, ou o contrário): não renderiza e pronto.
  // Os hooks acima já rodaram, então a ordem deles não muda — a saída tem de vir DEPOIS deles.
  if (!grupo) return null;

  if (grupo.role === "satellite") {
    return (
      <Panel title="Grupo comercial">
        <div className="rounded-md border border-gold/40 bg-gold-soft p-3 text-sm" role="alert">
          <p className="font-semibold text-gold-ink">Este evento é satélite de um grupo</p>
          <p className="mt-0.5 text-ink">
            A venda inteira está em{" "}
            {grupo.leader ? (
              <Link to={`/events/${grupo.leader.id}`} className="underline">
                {grupo.leader.title}
              </Link>
            ) : (
              "outro evento"
            )}
            . Os valores que este evento tinha antes de ser agrupado ficaram guardados na aba
            Histórico.
          </p>
        </div>
        {canGroup && (
          <div className="mt-3">
            <Button
              variant="outline"
              size="sm"
              loading={desagrupar.isPending}
              onClick={() => desagrupar.mutate()}
            >
              Desfazer agrupamento
            </Button>
            {desagrupar.isError && (
              <p className="mt-2 text-sm text-red">{desagrupar.error?.message}</p>
            )}
            <p className="mt-2 text-xs text-muted">
              Desagrupar devolve a edição da venda, mas com os campos vazios — os valores antigos
              estão no histórico, para redigitar.
            </p>
          </div>
        )}
      </Panel>
    );
  }

  if (grupo.role === "leader") {
    return (
      <Panel
        title="Grupo comercial"
        actions={
          canGroup && !editandoNome ? (
            <Button variant="outline" size="sm" onClick={() => setEditandoNome(true)}>
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              Nome
            </Button>
          ) : null
        }
      >
        {editandoNome ? (
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label className={LABEL_CLASS} htmlFor="grupo-nome-inline">
                Nome do grupo
              </label>
              <input
                id="grupo-nome-inline"
                className={INPUT_CLASS}
                value={nome}
                maxLength={200}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Sem nome, usa o título deste evento"
              />
            </div>
            <Button
              size="sm"
              loading={renomear.isPending}
              onClick={() =>
                renomear.mutate(nome.trim() || null, { onSuccess: () => setEditandoNome(false) })
              }
            >
              Salvar
            </Button>
            <Button variant="outline" size="sm" onClick={() => setEditandoNome(false)}>
              Cancelar
            </Button>
          </div>
        ) : (
          <>
            <p className="text-sm text-ink">
              Este é o evento <strong>principal</strong> de{" "}
              <strong>{grupo.display_name}</strong> — a venda do contrato inteiro está aqui.
            </p>
            {!grupo.group_name && (
              <p className="mt-0.5 text-xs text-muted">
                O grupo não tem nome; está usando o título deste evento.
              </p>
            )}
            <ul className="mt-3 divide-y divide-line">
              {grupo.satellites.map((s) => (
                <li key={s.id} className="flex items-center justify-between py-2 text-sm">
                  <span>
                    <Link to={`/events/${s.id}`} className="text-ink underline">
                      {s.title}
                    </Link>
                    <span className="ml-2 text-xs text-muted">{formatDay(s.start_at)}</span>
                  </span>
                  {canGroup && (
                    <Button
                      variant="outline"
                      size="sm"
                      loading={removerSatelite.isPending}
                      onClick={() => removerSatelite.mutate(s.id)}
                    >
                      Remover
                    </Button>
                  )}
                </li>
              ))}
            </ul>
            {removerSatelite.isError && (
              <p className="mt-2 text-sm text-red">{removerSatelite.error?.message}</p>
            )}
            {canGroup && (
              <div className="mt-3">
                <Button variant="outline" size="sm" onClick={() => setAgruparAberto(true)}>
                  Agrupar mais um evento
                </Button>
              </div>
            )}
          </>
        )}
        <AgruparEventosDialog data={data} open={agruparAberto} onOpenChange={setAgruparAberto} />
      </Panel>
    );
  }

  if (!canGroup) return null;

  return (
    <Panel title="Grupo comercial">
      <p className="text-sm text-muted">
        Este evento não faz parte de nenhum grupo. Agrupe quando o mesmo contrato tiver mais de um
        evento — a venda fica num principal só, e os relatórios param de contar em dobro.
      </p>
      <div className="mt-3">
        <Button variant="outline" size="sm" onClick={() => setAgruparAberto(true)}>
          Agrupar com outro evento
        </Button>
      </div>
      <AgruparEventosDialog data={data} open={agruparAberto} onOpenChange={setAgruparAberto} />
    </Panel>
  );
}

export interface ComercialSectionProps {
  data: EventoDetalhe;
}

/**
 * Bloco comercial da aba Comercial (feature 190; edição inline na 215).
 *
 * Ordem deliberada: primeiro com quem se vendeu (clientes e pré-contrato), depois quanto e
 * como, então de onde vem o número (o grupo, feature 246) e só por fim o resultado — que o
 * `KpiGrid` já agrega pelo grupo inteiro.
 */
export function ComercialSection({ data }: ComercialSectionProps) {
  return (
    <>
      {data.venda && <ClientesPanel data={data} />}
      {data.venda && <PreContratoPanel data={data} />}
      <VendaPanel data={data} />
      <ColecoesComerciaisPanel data={data} />
      <GrupoPanel data={data} />
      <KpiGrid data={data} />
    </>
  );
}
