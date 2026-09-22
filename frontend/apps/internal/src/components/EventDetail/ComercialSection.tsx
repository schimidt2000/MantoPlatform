import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Pencil } from "lucide-react";
import { Badge, Button } from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { MoneyInput } from "@manto/money";
import type { EventoDetalhe, RelatorioOrcamento } from "../../lib/agenda";
import { useEventCreateOptions } from "../../lib/eventCreate";
import {
  useSetEventClients,
  useSetEventFormResponse,
  useSetEventOrcamento,
  useUpdateEventComercial,
  type EventComercialInput,
} from "../../lib/eventInline";
import type { OrcamentoHistoricoEntry } from "../../lib/orcamento";
import {
  useDesagruparEvento,
  useRemoverSatelite,
  useRenomearGrupo,
} from "../../lib/eventOps";
import { ClientPicker, type SelectedClient } from "../ClientPicker";
import { FormResponsePicker, type SelectedFormResponse } from "../FormResponsePicker";
import { dataBr, OrcamentoPicker } from "../OrcamentoPicker";
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
  to,
  linkText = "ver na planilha",
}: {
  label: string;
  value: string;
  hint?: string;
  tone: "neutral" | "green" | "red";
  /** Destino do "ver na planilha" (feature 267) — omitido, o card não linka. */
  to?: string;
  linkText?: string;
}) {
  const toneClass =
    tone === "green" ? "text-green" : tone === "red" ? "text-red" : "text-ink";
  return (
    <div className="rounded-md border border-line bg-surface-2/60 p-3">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-0.5 text-lg font-semibold tabular-nums ${toneClass}`}>{value}</div>
      {hint && <div className="text-[11px] text-muted">{hint}</div>}
      {to && (
        <Link to={to} className="mt-1 inline-block text-[11px] text-blue underline">
          {linkText}
        </Link>
      )}
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
  const venda = data.venda;

  // Os DOIS meses são diferentes de propósito (feature 267): a comissão é escopada pela data da
  // VENDA e a planilha de pagamentos pela data do EVENTO. Um evento vendido em maio e realizado
  // em agosto tem os dois links em meses distintos — usar o mesmo entrega tela vazia.
  // Recorte por string: `start_at`/`sale_date` são horário de parede, e `new Date()` desloca +3h
  // (um evento do dia 1º às 00:00 escorregaria para o mês anterior).
  const linkComissoes =
    venda?.sale_date && venda?.seller_id
      ? `/financeiro/comissoes?mes=${venda.sale_date.slice(0, 7)}&vendedor=${venda.seller_id}&evento=${data.event.id}`
      : undefined;
  const linkPagamentos = data.event.start_at
    ? `/financeiro/pagamentos?mes=${data.event.start_at.slice(0, 7)}&busca=${encodeURIComponent(data.event.title)}`
    : undefined;

  return (
    <Panel
      title={`Resultado${kpi.group_size > 1 ? ` — grupo de ${kpi.group_size} eventos` : ""}`}
    >
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-5">
        <KpiCard label="Venda" value={brl(kpi.sale_value)} tone="neutral" />
        <KpiCard
          label="Custo (cachês)"
          value={brl(kpi.cost)}
          tone="neutral"
          to={linkPagamentos}
        />
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
          to={linkComissoes}
          linkText="ver em comissões"
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
function VendaForm({
  data,
  onClose,
  focarValor = false,
}: {
  data: EventoDetalhe;
  onClose: () => void;
  /** Aberto pelo "Pôr o valor" da Home: o foco já vai para o valor de venda final (feature 299). */
  focarValor?: boolean;
}) {
  const venda = data.venda!;
  const salvar = useUpdateEventComercial(data.event.id);
  // O valor de venda final (e não o bruto) é o que tira o evento de "Sem valor": o formulário não
  // deriva um do outro, e quem digitasse só o bruto salvaria e continuaria na lista (R46).
  const refValor = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (focarValor) refValor.current?.focus();
  }, [focarValor]);
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

  // O 400 do valor (feature 299, R43: R$ 0,01 não é venda) aparece no campo que o servidor nomeou,
  // com o texto dele — e não só como "Corrija os campos destacados" no rodapé —, e o foco vai até
  // esse campo (o bruto vem antes, como na edição completa).
  const camposDoErro = salvar.error instanceof ApiRequestError ? salvar.error.fields : undefined;
  const erroBruto = camposDoErro?.sale_value_gross;
  const erroFinal = camposDoErro?.sale_value;
  const erroDoValor = erroBruto ?? erroFinal;
  const refBruto = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (camposDoErro?.sale_value_gross) refBruto.current?.focus();
    else if (camposDoErro?.sale_value) refValor.current?.focus();
  }, [camposDoErro]);

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
            <label className={LABEL_CLASS} htmlFor="venda-bruto">
              Valor antes do desconto
            </label>
            <MoneyInput
              id="venda-bruto"
              ref={refBruto}
              className={`${MONEY_CLASS} ${erroBruto ? "border-red" : ""}`}
              value={form.sale_value_gross ?? 0}
              onValueChange={(v) => set("sale_value_gross", v)}
              aria-label="Valor antes do desconto"
            />
          </div>
          <div>
            <label className={LABEL_CLASS} htmlFor="venda-valor">
              Valor de venda final
            </label>
            <MoneyInput
              id="venda-valor"
              ref={refValor}
              className={`${MONEY_CLASS} ${erroFinal ? "border-red" : ""}`}
              value={form.sale_value ?? 0}
              onValueChange={(v) => set("sale_value", v)}
              aria-label="Valor de venda final"
            />
          </div>
        </div>
      )}
      {erroDoValor && (
        <p role="alert" className="text-sm text-red">
          {erroDoValor}
        </p>
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

/** Chips do que o orçamento vendeu — a mesma leitura que o servidor aplica ao evento. */
function chipsDoOrcamento(orc: NonNullable<EventoDetalhe["venda"]>["orcamento"]): string[] {
  if (!orc) return [];
  const chips: string[] = [];
  if (orc.fora_sp) {
    chips.push(
      `Fora de SP${orc.km_ida ? ` · ${orc.km_ida} km` : ""}${orc.deslocamento_cliente ? " · deslocamento da cliente" : ""}`,
    );
  }
  if (orc.coordenador_qty) {
    chips.push(`${orc.coordenador_qty} coordenador${orc.coordenador_qty > 1 ? "es" : ""}`);
  }
  if (orc.maquiagens) chips.push(`Maquiagem em ${orc.maquiagens}`);
  if (orc.cantores) chips.push(`${orc.cantores} cantor${orc.cantores > 1 ? "es" : ""}`);
  if (orc.has_show) chips.push("Show · técnico de som");
  return chips;
}

/**
 * Orçamento de origem (feature 273): o evento passa a saber o que foi vendido.
 *
 * Com orçamento: chips do que foi vendido, "Aplicar ao evento" (fora de SP + equipe — cria o que
 * falta, nunca remove), "Trocar", "Desvincular". Sem orçamento: busca no histórico e, em evento
 * sem venda, a opção de aplicar também os valores da duração escolhida (D1 do plano das ondas:
 * com venda digitada os valores ficam como estão). O evento importado do Google entra aqui
 * "mudo", e é por este painel que ele passa a ter equipe, fora de SP e teto de cachê.
 */
function OrcamentoPanel({ data }: { data: EventoDetalhe }) {
  const venda = data.venda!;
  const salvar = useSetEventOrcamento(data.event.id);
  const canEdit = Boolean(data.flags.can_edit_core);
  const orc = venda.orcamento;
  const [escolhido, setEscolhido] = useState<OrcamentoHistoricoEntry | null>(null);
  const [trocando, setTrocando] = useState(false);
  const [duracao, setDuracao] = useState<string>("");
  const [relatorio, setRelatorio] = useState<RelatorioOrcamento | null>(null);
  // Cortesia/permuta grava venda 0 de propósito: não é "sem venda" para aplicar valores. Desde a
  // 299 o valor simbólico (R$ 0,01) conta como "sem venda" — é pelo orçamento que ele vira venda.
  // Sem a chave (servidor antigo), a regra de antes.
  const semVenda = venda.sem_valor ?? (!venda.sale_value && !venda.is_cortesia_permuta);

  function enviar(id: number | null, extra: { aplicar_valores_duracao?: number | null } = {}) {
    setRelatorio(null);
    salvar.mutate(
      { orcamento_history_id: id, aplicar_equipe: true, ...extra },
      {
        onSuccess: (r) => {
          setRelatorio(r.relatorio_orcamento ?? null);
          setEscolhido(null);
          setTrocando(false);
          setDuracao("");
        },
      },
    );
  }

  const chips = chipsDoOrcamento(orc);
  const importadoSemVenda = venda.source === "google_calendar" && semVenda;
  // 409 "já vinculado a outro evento" / "satélite" mandam o id do evento certo: linka em vez de
  // deixar a comercial adivinhar.
  const detalhesDoErro = salvar.error instanceof ApiRequestError ? salvar.error.details : undefined;
  const eventoDoErro = [detalhesDoErro?.event_id, detalhesDoErro?.leader_id].find(
    (v): v is number => typeof v === "number",
  );
  // feature 301 — antes isto era `!orc && venda.tem_orcamento`: "o servidor não me deu o
  // orçamento, logo é de outro". Com a visibilidade restaurada o servidor SEMPRE manda, então
  // essa dedução seria eternamente falsa e os três botões apareceriam para todo mundo — para o
  // servidor recusar depois do clique. Quem decide agora é `pode_gerir` (Princípio XIII).
  const semAcessoAoOrcamento = !orc && venda.tem_orcamento;
  const podeGerirOrcamento = orc ? orc.pode_gerir : true;

  if (!canEdit) {
    return (
      <Panel title="Orçamento">
        {orc ? (
          <DataRow label={orc.client_name || "Orçamento"}>
            <Link to={`/orcamento/${orc.id}`} className="text-blue underline">
              Abrir orçamento
            </Link>
          </DataRow>
        ) : (
          <Empty>
            {venda.tem_orcamento
              ? "Vinculado a um orçamento que o seu perfil não abre."
              : "Nenhum orçamento vinculado."}
          </Empty>
        )}
      </Panel>
    );
  }

  return (
    <Panel title="Orçamento">
      {semAcessoAoOrcamento ? (
        <p className="text-sm text-muted">
          Vinculado a um orçamento que o seu perfil não abre.
        </p>
      ) : orc && !trocando ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium text-ink">{orc.client_name || "Sem cliente"}</span>
            {orc.event_date && <span className="text-muted">{dataBr(orc.event_date)}</span>}
            {/* feature 301 — de quem é o orçamento. A lista virou do time inteiro, e é este
                nome que a recusa cita quando alguém tenta mexer no vínculo alheio. */}
            <span className="text-muted">por {orc.autor}</span>
            <Link to={`/orcamento/${orc.id}`} className="text-blue underline">
              Abrir orçamento
            </Link>
          </div>
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {chips.map((chip) => (
                <Badge key={chip} tone={chip.startsWith("Fora de SP") ? "gold" : "neutral"}>
                  {chip}
                </Badge>
              ))}
            </div>
          )}
          {podeGerirOrcamento ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="sm"
                loading={salvar.isPending}
                onClick={() => enviar(orc.id)}
                title="Cria o que falta (coordenadores, maquiador, técnico de som), marca maquiagem e fora de SP. Nunca remove nada."
              >
                Aplicar ao evento
              </Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => setTrocando(true)}>
                Trocar
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={salvar.isPending}
                onClick={() => enviar(null)}
              >
                Desvincular
              </Button>
            </div>
          ) : (
            /* feature 301 — vê tudo, mexe em nada: a venda é de quem fez o orçamento. Diz de
               quem é e qual a saída, em vez de sumir com o bloco ou oferecer botão que falha. */
            <p className="text-sm text-muted">
              Este orçamento é de {orc.autor} — só {orc.autor} ou o superadmin podem trocar,
              desvincular ou re-aplicar.
            </p>
          )}
        </div>
      ) : escolhido ? (
        <div className="space-y-2">
          <div className="text-sm text-ink">
            <span className="font-medium">{escolhido.client_name || "Sem cliente"}</span>
            {escolhido.event_date && (
              <span className="ml-2 text-muted">{dataBr(escolhido.event_date)}</span>
            )}
            {escolhido.event_id != null && escolhido.event_id !== data.event.id && (
              <span className="ml-2 text-red">já vinculado a outro evento</span>
            )}
          </div>
          {semVenda && (
            <label className="flex flex-wrap items-center gap-2 text-sm text-ink">
              Aplicar também os valores de
              <select
                className={INPUT_CLASS}
                value={duracao}
                onChange={(e) => setDuracao(e.target.value)}
                aria-label="Duração dos valores do orçamento"
              >
                <option value="">não aplicar valores</option>
                <option value="1">1h — {brl(escolhido.total_1h)}</option>
                <option value="2">2h — {brl(escolhido.total_2h)}</option>
                <option value="3">3h — {brl(escolhido.total_3h)}</option>
                <option value="4">4h — {brl(escolhido.total_4h)}</option>
              </select>
            </label>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              loading={salvar.isPending}
              onClick={() =>
                enviar(escolhido.id, {
                  aplicar_valores_duracao: duracao ? Number(duracao) : null,
                })
              }
            >
              Vincular e aplicar
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setEscolhido(null);
                setTrocando(false);
              }}
            >
              Cancelar
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {importadoSemVenda && (
            <p className="text-xs text-muted">
              Evento importado do Google, sem venda: vincule o orçamento para trazer a equipe, o
              fora de SP e, se quiser, os valores.
            </p>
          )}
          <OrcamentoPicker onChange={setEscolhido} />
          {trocando && (
            <Button type="button" variant="ghost" size="sm" onClick={() => setTrocando(false)}>
              Cancelar
            </Button>
          )}
        </div>
      )}
      {salvar.isPending && <p className="mt-1 text-sm text-muted">Aplicando…</p>}
      {salvar.isError && (
        <p className="mt-1 text-sm text-red" role="alert">
          {salvar.error?.message}
          {eventoDoErro != null && (
            <>
              {" "}
              <Link to={`/events/${eventoDoErro}`} className="underline">
                Abrir esse evento
              </Link>
            </>
          )}
        </p>
      )}
      {relatorio && !salvar.isPending && (
        <p className="mt-1 text-sm text-ink" role="status">
          {relatorio.frase}
          {(relatorio.nao_casados?.length ?? 0) > 0 && (
            <span className="block text-xs text-muted">
              Sem papel correspondente no evento: {relatorio.nao_casados!.join(", ")}.
            </span>
          )}
        </p>
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
  const [searchParams, setSearchParams] = useSearchParams();
  // "Pôr o valor", na Home, abre a venda já em edição (feature 299, SC-007: dois cliques — este e
  // "Salvar venda"). Sem permissão de editar, o parâmetro é ignorado.
  const pedeEdicao = searchParams.get("editar") === "venda";
  const [editando, setEditando] = useState(pedeEdicao);
  if (!venda) return null;
  const bruto = venda.sale_value_gross ?? 0;
  const liquido = venda.sale_value ?? 0;
  const desconto = bruto > liquido ? bruto - liquido : 0;
  // Satélite não edita venda: o dinheiro do contrato mora no principal, e o servidor recusa o
  // PATCH com 409. Sem esta trava o botão existia, a pessoa preenchia e só descobria no envio.
  const canEdit = Boolean(data.flags.can_edit_core) && !data.event.is_satellite;

  // Ao salvar ou cancelar, o `editar` sai da URL (preservando a aba) — senão recarregar a página
  // reabriria a edição.
  const fechar = () => {
    setEditando(false);
    if (!pedeEdicao) return;
    setSearchParams(
      (atual) => {
        const proximo = new URLSearchParams(atual);
        proximo.delete("editar");
        return proximo;
      },
      { replace: true },
    );
  };

  if (editando && canEdit) {
    return (
      <Panel title="Comercial — dados da venda">
        <VendaForm data={data} onClose={fechar} focarValor={pedeEdicao} />
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
        {/* Feature 299: vazio ou zero é "A definir", nunca "R$ 0,00"; o R$ 0,01 aparece como está,
            marcado; no outro evento de um grupo a venda mora no principal. O quadrinho "Venda" do
            Resultado continua com o número, porque é indicador financeiro. */}
        <DataRow label="Valor de venda final">
          {data.event.is_satellite ? (
            <span>
              no evento principal
              {data.event.group?.leader && (
                <>
                  {" — "}
                  <Link
                    to={`/events/${data.event.group.leader.id}?aba=comercial`}
                    className="text-blue underline"
                  >
                    abrir
                  </Link>
                </>
              )}
            </span>
          ) : venda.a_definir ? (
            <span className="font-semibold text-gold-ink">A definir</span>
          ) : (
            <span className="font-semibold tabular-nums">
              {brl(liquido)}
              {venda.valor_simbolico && (
                <Badge tone="gold" className="ml-2">
                  valor simbólico
                </Badge>
              )}
            </span>
          )}
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
      {data.venda && <OrcamentoPanel data={data} />}
      {data.venda && <PreContratoPanel data={data} />}
      <VendaPanel data={data} />
      <ColecoesComerciaisPanel data={data} />
      <GrupoPanel data={data} />
      <KpiGrid data={data} />
    </>
  );
}
