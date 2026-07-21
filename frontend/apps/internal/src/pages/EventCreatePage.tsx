import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import { MoneyInput, formatBRL } from "@manto/money";
import { ApiRequestError } from "@manto/api-client";
import { useCurrentUser } from "../lib/useAuth";
import {
  useCreateEvent,
  useEventCreateOptions,
  useOrcamentoPrefill,
  type CharacterInput,
  type ClientLinkInput,
  type EventCreateInput,
  type ObservationInput,
  type OrcamentoCache,
} from "../lib/eventCreate";
import { ClientPicker } from "../components/ClientPicker";
import { FormResponsePicker, type SelectedFormResponse } from "../components/FormResponsePicker";

const eventSchema = z
  .object({
    title: z.string().min(1, "Título obrigatório"),
    event_type: z.string(),
    date: z.string().min(1, "Data obrigatória"),
    start: z.string().min(1, "Informe o horário de início"),
    end: z.string().min(1, "Informe o horário de fim"),
    location: z.string(),
    description: z.string(),
    needs_rehearsal: z.boolean(),
    is_cortesia_permuta: z.boolean(),
    sale_value: z.number(),
    sale_value_gross: z.number(),
    transport_value: z.number(),
    acrescimo_value: z.number(),
    with_invoice: z.boolean(),
    seller_id: z.string().min(1, "Selecione o vendedor responsável"),
    sale_date: z.string(),
    payment_method: z.string(),
    payment_installments: z.string(),
    payment_due_date: z.string(),
  })
  .refine((v) => v.is_cortesia_permuta || v.sale_value_gross > 0, {
    message: "Informe o valor antes do desconto.",
    path: ["sale_value_gross"],
  })
  .refine((v) => v.is_cortesia_permuta || v.sale_value > 0, {
    message: "Informe o valor de venda.",
    path: ["sale_value"],
  })
  .refine(
    (v) =>
      v.payment_method !== "pix_parcelado" ||
      (Number(v.payment_installments) >= 2 && Number(v.payment_installments) <= 12),
    { message: "Informe o número de parcelas (2 a 12).", path: ["payment_installments"] },
  )
  .refine((v) => v.start === "" || v.end === "" || v.start !== v.end, {
    message: "Horário de fim deve ser diferente do início.",
    path: ["end"],
  });

type EventFormValues = z.infer<typeof eventSchema>;

/** Mapa campo-do-servidor → campo do formulário React, para destacar erros de validação (400). */
const SERVER_FIELD_MAP: Partial<Record<string, keyof EventFormValues>> = {
  title: "title",
  event_date: "date",
  event_time: "start",
  sale_value_gross: "sale_value_gross",
  sale_value: "sale_value",
  seller_id: "seller_id",
  payment_installments: "payment_installments",
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  );
}

const FIELD = "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
const LABEL = "mb-1 block text-sm text-muted";

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p className="mt-1 text-sm text-red" role="alert">
      {message}
    </p>
  );
}

interface CharacterRowProps {
  value: CharacterInput;
  onChange: (next: CharacterInput) => void;
  onRemove: () => void;
  figurinoSheets: { id: number; character_name: string }[];
  talents: { id: number; name: string }[];
}

function CharacterRow({ value, onChange, onRemove, figurinoSheets, talents }: CharacterRowProps) {
  return (
    <li className="space-y-2 border-b border-line pb-3 last:border-none">
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="h-11 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          placeholder="Personagem / função"
          value={value.name}
          onChange={(e) => onChange({ ...value, name: e.target.value })}
          aria-label="Nome do personagem"
        />
        <Button type="button" variant="ghost" size="sm" onClick={onRemove} aria-label="Remover">
          ✕
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={value.figurino_sheet_id ?? ""}
          onChange={(e) =>
            onChange({
              ...value,
              figurino_sheet_id: e.target.value ? Number(e.target.value) : null,
            })
          }
          aria-label="Ficha de figurino"
        >
          <option value="">Figurino: auto-detectar pelo nome</option>
          {figurinoSheets.map((s) => (
            <option key={s.id} value={s.id}>
              {s.character_name}
            </option>
          ))}
        </select>
        <select
          className="h-10 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={value.talent_id ?? ""}
          onChange={(e) =>
            onChange({ ...value, talent_id: e.target.value ? Number(e.target.value) : null })
          }
          aria-label="Pré-escalar talento"
        >
          <option value="">— pré-escalar talento (opcional) —</option>
          {talents.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <MoneyInput
          className="h-10 w-28 rounded-md border border-line bg-panel px-2 text-sm text-ink"
          value={value.cache_value ?? 0}
          onValueChange={(v) => onChange({ ...value, cache_value: v })}
          aria-label="Cachê"
        />
        <label className="flex items-center gap-1.5 text-sm text-ink">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={value.needs_makeup}
            onChange={(e) => onChange({ ...value, needs_makeup: e.target.checked })}
          />
          Maquiagem
        </label>
        <label className="flex items-center gap-1.5 text-sm text-ink">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={value.is_singer}
            onChange={(e) => onChange({ ...value, is_singer: e.target.checked })}
          />
          Cantor(a)
        </label>
      </div>
    </li>
  );
}

export function EventCreatePage() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const [searchParams] = useSearchParams();
  const orcamentoIdParam = searchParams.get("orcamento_id");
  const orcamentoId = orcamentoIdParam ? Number(orcamentoIdParam) : null;

  const currentUser = useCurrentUser();
  const options = useEventCreateOptions();
  const prefill = useOrcamentoPrefill(orcamentoId);
  const createEvent = useCreateEvent();

  const [serverError, setServerError] = useState<string | null>(null);
  const [duracao, setDuracao] = useState("1");
  const [orcCaches, setOrcCaches] = useState<OrcamentoCache[]>([]);
  const [characters, setCharacters] = useState<CharacterInput[]>([]);
  const [coordinatorTalentId, setCoordinatorTalentId] = useState<number | null>(null);
  const [clients, setClients] = useState<(ClientLinkInput & { name: string })[]>([]);
  const [formResponse, setFormResponse] = useState<SelectedFormResponse | null>(null);
  const [hasReembolso, setHasReembolso] = useState(false);
  const [reembolsoDescription, setReembolsoDescription] = useState("");
  const [reembolsoAmount, setReembolsoAmount] = useState(0);
  const [observations, setObservations] = useState<ObservationInput[]>([]);
  const [newObsType, setNewObsType] = useState<"text" | "link">("text");
  const [newObsContent, setNewObsContent] = useState("");
  const [newObsLabel, setNewObsLabel] = useState("");

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<EventFormValues>({
    resolver: zodResolver(eventSchema),
    defaultValues: {
      title: "",
      event_type: "",
      date: "",
      start: "",
      end: "",
      location: "",
      description: "",
      needs_rehearsal: false,
      is_cortesia_permuta: false,
      sale_value: 0,
      sale_value_gross: 0,
      transport_value: 0,
      acrescimo_value: 0,
      with_invoice: false,
      seller_id: "",
      sale_date: "",
      payment_method: "",
      payment_installments: "",
      payment_due_date: "",
    },
  });

  const eventType = watch("event_type");
  const isCortesia = watch("is_cortesia_permuta");
  const paymentMethod = watch("payment_method");

  // Pré-fill do orçamento: campos essenciais + elenco a partir dos cachês (feature 152, US4).
  useEffect(() => {
    if (!prefill.data?.orcamento_id) return;
    const p = prefill.data;
    if (p.date) setValue("date", p.date);
    if (p.start_time) setValue("start", p.start_time);
    if (p.location) setValue("location", p.location);
    setValue("sale_value_gross", p.total_1h ?? 0);
    setValue("sale_value", p.total_1h ?? 0);
    setValue("transport_value", p.transport_value ?? 0);
    setValue("acrescimo_value", p.acrescimo_value ?? 0);
    setValue("with_invoice", Boolean(p.with_invoice));
    setOrcCaches(p.caches ?? []);
    setCharacters(
      (p.caches ?? []).map((c) => ({
        name: c.label,
        figurino_sheet_id: null,
        cache_value: null,
        needs_makeup: c.needs_makeup,
        is_singer: c.is_singer,
        talent_id: null,
      })),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill.data?.orcamento_id]);

  // Default do vendedor: o próprio usuário, se ele estiver na lista de vendedores.
  useEffect(() => {
    if (!options.data || !currentUser.data) return;
    const isSeller = options.data.sellers.some((s) => s.id === currentUser.data!.id);
    if (isSeller) setValue("seller_id", String(currentUser.data.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.data, currentUser.data]);

  const selectDuracao = (dur: "1" | "2" | "3" | "4") => {
    setDuracao(dur);
    if (!prefill.data) return;
    const total = prefill.data[`total_${dur}h` as "total_1h"] ?? 0;
    setValue("sale_value_gross", total);
    setValue("sale_value", total);
  };

  const addCharacter = () =>
    setCharacters((prev) => [
      ...prev,
      {
        name: "",
        figurino_sheet_id: null,
        cache_value: null,
        needs_makeup: false,
        is_singer: false,
        talent_id: null,
      },
    ]);

  const addObservation = () => {
    if (!newObsContent.trim()) return;
    setObservations((prev) => [
      ...prev,
      { obs_type: newObsType, content: newObsContent.trim(), label: newObsLabel.trim() },
    ]);
    setNewObsContent("");
    setNewObsLabel("");
  };

  const onSubmit = handleSubmit((values) => {
    setServerError(null);
    const payload: EventCreateInput = {
      title: values.title,
      event_type: values.event_type,
      date: values.date,
      start: values.start,
      end: values.end,
      location: values.location,
      description: values.description,
      needs_rehearsal: values.needs_rehearsal || values.event_type === "SHOW",
      sale_value: values.is_cortesia_permuta ? 0 : values.sale_value,
      sale_value_gross: values.is_cortesia_permuta ? 0 : values.sale_value_gross,
      transport_value: values.transport_value,
      acrescimo_value: values.acrescimo_value,
      with_invoice: values.with_invoice,
      is_cortesia_permuta: values.is_cortesia_permuta,
      seller_id: values.seller_id ? Number(values.seller_id) : null,
      sale_date: values.sale_date || null,
      payment_method: values.payment_method || null,
      payment_installments: values.payment_installments
        ? Number(values.payment_installments)
        : null,
      payment_due_date: values.payment_due_date || null,
      orcamento_history_id: orcamentoId,
      duracao,
      characters: characters.filter((c) => c.name.trim().length > 0),
      orc_caches: orcCaches,
      acrescimos: [],
      coordinator_talent_id: coordinatorTalentId,
      clients: clients.map(({ client_id, relation }) => ({ client_id, relation })),
      form_response_id: formResponse?.id ?? null,
      has_reembolso: hasReembolso,
      reembolso_description: reembolsoDescription,
      reembolso_amount: reembolsoAmount,
      observations,
    };

    createEvent.mutate(payload, {
      onSuccess: (result) => navigate(`/events/${result.event.id}`),
      onError: (error) => {
        if (error instanceof ApiRequestError && error.fields) {
          const messages: string[] = [];
          for (const [field, message] of Object.entries(error.fields)) {
            messages.push(message);
            const rhfField = SERVER_FIELD_MAP[field];
            if (rhfField) setError(rhfField, { message });
          }
          setServerError(messages.join(" "));
          return;
        }
        setServerError(error.message);
      },
    });
  });

  if (options.isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (options.isError || !options.data) {
    return (
      <div className="mx-auto max-w-3xl p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o formulário de criação.
        </div>
      </div>
    );
  }

  const opts = options.data;

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <div className="mb-4">
        <Button asChild variant="ghost" size="sm">
          <Link to="/agenda">‹ Agenda</Link>
        </Button>
      </div>

      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
      >
        <h1 className="mb-4 text-2xl font-semibold text-ink">Novo evento</h1>

        <form onSubmit={onSubmit} noValidate className="space-y-4">
          <Section title="Dados do evento">
            <div>
              <label className={LABEL} htmlFor="title">
                Título *
              </label>
              <input id="title" className={FIELD} {...register("title")} />
              <FieldError message={errors.title?.message} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL} htmlFor="event_type">
                  Tipo de evento
                </label>
                <select id="event_type" className={FIELD} {...register("event_type")}>
                  <option value="">— Selecionar —</option>
                  <option value="SHOW">SHOW — Show com som</option>
                  <option value="CORP">CORP — Corporativo</option>
                  <option value="R&I">R&amp;I — Receptivo e Interativo</option>
                  <option value="VM">VM — Visita Mágica</option>
                </select>
              </div>
              <div>
                <label className={LABEL} htmlFor="date">
                  Data *
                </label>
                <input id="date" type="date" className={FIELD} {...register("date")} />
                <FieldError message={errors.date?.message} />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL} htmlFor="start">
                  Horário de início *
                </label>
                <input id="start" type="time" className={FIELD} {...register("start")} />
                <FieldError message={errors.start?.message} />
              </div>
              <div>
                <label className={LABEL} htmlFor="end">
                  Horário de fim *
                </label>
                <input id="end" type="time" className={FIELD} {...register("end")} />
                <FieldError message={errors.end?.message} />
              </div>
            </div>
            <div>
              <label className={LABEL} htmlFor="location">
                Local do evento
              </label>
              <input id="location" className={FIELD} {...register("location")} />
            </div>
            <div>
              <label className={LABEL} htmlFor="description">
                Descrição
              </label>
              <textarea id="description" rows={3} className={FIELD} {...register("description")} />
            </div>
            {eventType !== "SHOW" && (
              <label className="flex items-center gap-2 text-sm text-ink">
                <input type="checkbox" className="h-5 w-5" {...register("needs_rehearsal")} />
                Precisa de ensaio
              </label>
            )}
          </Section>

          {prefill.data?.orcamento_id && (
            <Section title="Origem: orçamento">
              <p className="text-sm text-muted">
                Criando a partir do orçamento de{" "}
                <strong>{prefill.data.client_name || "cliente"}</strong>.
              </p>
              <div className="flex flex-wrap gap-2">
                {(["1", "2", "3", "4"] as const).map((dur) => (
                  <button
                    key={dur}
                    type="button"
                    onClick={() => selectDuracao(dur)}
                    className={`rounded-md border px-3 py-2 text-sm ${
                      duracao === dur
                        ? "border-accent bg-accent-soft text-ink"
                        : "border-line bg-panel text-ink"
                    }`}
                  >
                    {dur}h — R$ {formatBRL(prefill.data[`total_${dur}h` as "total_1h"] ?? 0)}
                  </button>
                ))}
              </div>
            </Section>
          )}

          <Section title="Financeiro">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" className="h-5 w-5" {...register("is_cortesia_permuta")} />
              Cortesia / permuta (sem venda em dinheiro)
            </label>
            <AnimatePresence initial={false}>
              {!isCortesia && (
                <motion.div
                  initial={reduceMotion ? false : { height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="space-y-3 overflow-hidden"
                >
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className={LABEL}>Valor antes do desconto *</label>
                      <MoneyInput
                        className={FIELD}
                        value={watch("sale_value_gross")}
                        onValueChange={(v) => setValue("sale_value_gross", v)}
                      />
                      <FieldError message={errors.sale_value_gross?.message} />
                    </div>
                    <div>
                      <label className={LABEL}>Valor de venda *</label>
                      <MoneyInput
                        className={FIELD}
                        value={watch("sale_value")}
                        onValueChange={(v) => setValue("sale_value", v)}
                      />
                      <FieldError message={errors.sale_value?.message} />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={LABEL}>Transporte</label>
                <MoneyInput
                  className={FIELD}
                  value={watch("transport_value")}
                  onValueChange={(v) => setValue("transport_value", v)}
                />
              </div>
              <div>
                <label className={LABEL}>Acréscimo</label>
                <MoneyInput
                  className={FIELD}
                  value={watch("acrescimo_value")}
                  onValueChange={(v) => setValue("acrescimo_value", v)}
                />
              </div>
            </div>
            <div>
              <label className={LABEL} htmlFor="seller_id">
                Vendedor responsável *
              </label>
              <select id="seller_id" className={FIELD} {...register("seller_id")}>
                <option value="">— Selecionar —</option>
                {opts.sellers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <FieldError message={errors.seller_id?.message} />
            </div>
            <div>
              <label className={LABEL} htmlFor="sale_date">
                Data da venda
              </label>
              <input id="sale_date" type="date" className={FIELD} {...register("sale_date")} />
            </div>
            <div>
              <label className={LABEL} htmlFor="payment_method">
                Forma de pagamento
              </label>
              <select id="payment_method" className={FIELD} {...register("payment_method")}>
                <option value="">— Selecionar —</option>
                <option value="avista">À vista (PIX)</option>
                <option value="pix_parcelado">Dividido no PIX</option>
                <option value="faturado">Faturado</option>
                <option value="cartao">Cartão de crédito</option>
              </select>
            </div>
            {paymentMethod === "pix_parcelado" && (
              <div>
                <label className={LABEL} htmlFor="payment_installments">
                  Número de parcelas (2 a 12) *
                </label>
                <input
                  id="payment_installments"
                  type="number"
                  min={2}
                  max={12}
                  className={FIELD}
                  {...register("payment_installments")}
                />
                <FieldError message={errors.payment_installments?.message} />
              </div>
            )}
            <div>
              <label className={LABEL} htmlFor="payment_due_date">
                Vencimento do pagamento
              </label>
              <input
                id="payment_due_date"
                type="date"
                className={FIELD}
                {...register("payment_due_date")}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" className="h-5 w-5" {...register("with_invoice")} />
              Venda com nota fiscal
            </label>
          </Section>

          <Section title="Elenco">
            <ul className="space-y-3">
              {characters.map((c, i) => (
                <CharacterRow
                  key={i}
                  value={c}
                  onChange={(next) =>
                    setCharacters((prev) => prev.map((p, j) => (j === i ? next : p)))
                  }
                  onRemove={() => setCharacters((prev) => prev.filter((_, j) => j !== i))}
                  figurinoSheets={opts.figurino_sheets}
                  talents={opts.assignable_talents}
                />
              ))}
            </ul>
            <Button type="button" variant="outline" size="sm" onClick={addCharacter}>
              Adicionar personagem
            </Button>
            <div className="border-t border-line pt-3">
              <label className={LABEL} htmlFor="coordinator">
                Pré-escalar coordenador (opcional)
              </label>
              <select
                id="coordinator"
                className={FIELD}
                value={coordinatorTalentId ?? ""}
                onChange={(e) =>
                  setCoordinatorTalentId(e.target.value ? Number(e.target.value) : null)
                }
              >
                <option value="">— sem pré-escala —</option>
                {opts.assignable_talents.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </Section>

          <Section title="Cliente e pré-contrato">
            <div>
              <label className={LABEL}>Clientes associados</label>
              <ClientPicker
                value={clients}
                onChange={setClients}
                relationOptions={opts.client_relation_tipos}
              />
            </div>
            <div>
              <label className={LABEL}>Pré-contrato (formulário recebido)</label>
              <FormResponsePicker value={formResponse} onChange={setFormResponse} />
            </div>
          </Section>

          <Section title="Reembolso a cobrar da cliente">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                className="h-5 w-5"
                checked={hasReembolso}
                onChange={(e) => setHasReembolso(e.target.checked)}
              />
              Este evento tem um reembolso a cobrar
            </label>
            {hasReembolso && (
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className={LABEL}>Descrição</label>
                  <input
                    className={FIELD}
                    value={reembolsoDescription}
                    onChange={(e) => setReembolsoDescription(e.target.value)}
                  />
                </div>
                <div>
                  <label className={LABEL}>Valor</label>
                  <MoneyInput
                    className={FIELD}
                    value={reembolsoAmount}
                    onValueChange={setReembolsoAmount}
                  />
                </div>
              </div>
            )}
          </Section>

          <Section title="Observações">
            {observations.length > 0 && (
              <ul className="divide-y divide-line">
                {observations.map((o, i) => (
                  <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <span className="text-ink">
                      {o.label && <span className="mr-2 text-xs text-muted">{o.label}</span>}
                      {o.content}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setObservations((prev) => prev.filter((_, j) => j !== i))}
                    >
                      ✕
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <select
                className="h-11 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                value={newObsType}
                onChange={(e) => setNewObsType(e.target.value as "text" | "link")}
              >
                <option value="text">Texto</option>
                <option value="link">Link</option>
              </select>
              <input
                className="h-11 min-w-40 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                placeholder={newObsType === "link" ? "https://…" : "Escreva a observação"}
                value={newObsContent}
                onChange={(e) => setNewObsContent(e.target.value)}
              />
              <input
                className="h-11 w-32 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                placeholder="Rótulo (opcional)"
                value={newObsLabel}
                onChange={(e) => setNewObsLabel(e.target.value)}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!newObsContent.trim()}
                onClick={addObservation}
              >
                Adicionar
              </Button>
            </div>
            <p className="text-xs text-muted">
              Observações com imagem podem ser adicionadas depois, no detalhe do evento.
            </p>
          </Section>

          {serverError && (
            <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
              {serverError}
            </div>
          )}

          <div className="flex justify-end">
            <Button type="submit" loading={isSubmitting || createEvent.isPending}>
              {createEvent.isPending ? "Criando..." : "Criar evento"}
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
