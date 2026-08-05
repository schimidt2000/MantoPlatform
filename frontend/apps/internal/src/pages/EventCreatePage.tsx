import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion, useReducedMotion } from "framer-motion";
import { Button, PageHeader, Skeleton, Card, CardContent } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { ApiRequestError } from "@manto/api-client";
import { useCurrentUser } from "../lib/useAuth";
import {
  eventSchema,
  DEFAULT_EVENT_FORM_VALUES,
  FIELD_ORDER,
  SERVER_FIELD_MAP,
  type EventFormValues,
} from "../lib/eventFormSchema";
import {
  useCreateEvent,
  useEventCreateOptions,
  useOrcamentoPrefill,
  type CharacterInput,
  type ClientLinkInput,
  type EventCreateInput,
  type ObservationInput,
  type OrcamentoCache,
  type PendingPaymentProof,
} from "../lib/eventCreate";
import { enviarComprovante, enviarContrato, enviarReembolso } from "../lib/eventAttachments";
import { enviarObservacaoComFoto } from "../lib/observations";
import { useFormResponseDetail } from "../lib/formulariosAdmin";
import type { SelectedFormResponse } from "../components/FormResponsePicker";
import { ClienteBlock } from "../components/EventFormBlocks/ClienteBlock";
import { DadosEventoBlock } from "../components/EventFormBlocks/DadosEventoBlock";
import { ElencoBlock } from "../components/EventFormBlocks/ElencoBlock";
import { ValoresBlock } from "../components/EventFormBlocks/ValoresBlock";
import { PagamentoBlock } from "../components/EventFormBlocks/PagamentoBlock";
import { ContratoBlock } from "../components/EventFormBlocks/ContratoBlock";
import { ObservacoesBlock } from "../components/EventFormBlocks/ObservacoesBlock";
import { PendingAttachmentsPanel, type AttachmentUploadStatus } from "../components/PendingAttachmentsPanel";

/** Um anexo pendente de envio na fase 2 (feature 184) — guarda os dados originais para permitir
 * "Tentar novamente" sem o usuário re-selecionar o arquivo. */
type PendingAttachment =
  | { id: string; kind: "payment"; proof: PendingPaymentProof }
  | { id: string; kind: "contract"; file: File; signed: boolean }
  | { id: string; kind: "reimbursement"; description: string; amount: number; file: File | null }
  | { id: string; kind: "observation-image"; content: string; label: string; file: File };

export function EventCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const reduceMotion = useReducedMotion();
  const [searchParams] = useSearchParams();
  const orcamentoIdParam = searchParams.get("orcamento_id");
  const orcamentoId = orcamentoIdParam ? Number(orcamentoIdParam) : null;
  // Pré-preenchimento a partir de uma resposta de formulário (tela `/formularios` → "Criar
  // evento com os dados desta resposta"). Reusa o detalhe já exposto pela API, com o mesmo
  // RBAC (_require_vendas) de quem cria evento — sem endpoint novo.
  const formResponseIdParam = searchParams.get("form_response_id");
  const formResponseId = formResponseIdParam ? Number(formResponseIdParam) : null;

  const currentUser = useCurrentUser();
  const options = useEventCreateOptions();
  const prefill = useOrcamentoPrefill(orcamentoId);
  const formResponsePrefill = useFormResponseDetail(formResponseId);
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
  const [reembolsoInvoiceFile, setReembolsoInvoiceFile] = useState<File | null>(null);
  const [paymentProofs, setPaymentProofs] = useState<PendingPaymentProof[]>([]);
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [contractSigned, setContractSigned] = useState(false);
  const [observations, setObservations] = useState<ObservationInput[]>([]);

  const [createdEventId, setCreatedEventId] = useState<number | null>(null);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [attachmentStatus, setAttachmentStatus] = useState<Record<string, AttachmentUploadStatus>>({});

  const formRef = useRef<HTMLFormElement>(null);

  const methods = useForm<EventFormValues>({
    resolver: zodResolver(eventSchema),
    mode: "onBlur",
    defaultValues: DEFAULT_EVENT_FORM_VALUES,
  });
  const { handleSubmit, setError, setValue, setFocus, formState } = methods;
  const { errors, isSubmitting } = formState;

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
        role_id: null,
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

  // Pré-fill da resposta de formulário: já deixa o pré-contrato vinculado, a data do evento
  // preenchida e o cliente associado (quando a resposta já tem um) na lista de clientes.
  useEffect(() => {
    const r = formResponsePrefill.data?.response;
    if (!r) return;
    setFormResponse({ id: r.id, name: r.contact_name, form_type: r.form_type_label });
    if (r.event_date) setValue("date", r.event_date.slice(0, 10));
    if (r.client_id) {
      setClients((current) =>
        current.some((c) => c.client_id === r.client_id)
          ? current
          : [
              ...current,
              {
                client_id: r.client_id!,
                name: r.client_name ?? r.contact_name,
                relation: "Contratante",
              },
            ],
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formResponsePrefill.data?.response?.id]);

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

  // ── Fase 2: upload de anexos pendentes, depois que o evento já existe ──────────
  //
  // O `eventId` vem por ARGUMENTO, não de um hook criado no render. `setCreatedEventId` só tem
  // efeito no render seguinte, e a fase 2 dispara ainda dentro do `onSuccess` da criação — hooks
  // como `useAddPayment(createdEventId ?? 0)` ficariam presos em `0` e todo anexo iria para
  // `POST /api/events/0/...` → 404. Era isso que fazia o comprovante "sempre falhar" logo depois
  // da mensagem de evento criado.
  const uploadOne = async (item: PendingAttachment, eventId: number) => {
    setAttachmentStatus((s) => ({ ...s, [item.id]: "uploading" }));
    try {
      let atualizado;
      if (item.kind === "payment") {
        atualizado = await enviarComprovante(eventId, {
          amount: item.proof.amount,
          file: item.proof.file,
        });
      } else if (item.kind === "contract") {
        atualizado = await enviarContrato(eventId, { file: item.file, is_signed: item.signed });
      } else if (item.kind === "reimbursement") {
        atualizado = await enviarReembolso(eventId, {
          description: item.description,
          amount: item.amount,
          file: item.file ?? undefined,
        });
      } else {
        atualizado = await enviarObservacaoComFoto(eventId, {
          file: item.file,
          label: item.label || undefined,
        });
      }
      // Semeia o cache do detalhe para a navegação seguinte já abrir com o anexo no lugar.
      queryClient.setQueryData(["event", eventId], atualizado);
      setAttachmentStatus((s) => ({ ...s, [item.id]: "success" }));
    } catch {
      setAttachmentStatus((s) => ({ ...s, [item.id]: "error" }));
    }
  };

  const runUploads = async (items: PendingAttachment[], eventId: number) => {
    for (const item of items) {
      // eslint-disable-next-line no-await-in-loop
      await uploadOne(item, eventId);
    }
  };

  const retryAttachment = (id: string) => {
    const item = attachments.find((a) => a.id === id);
    if (item && createdEventId) uploadOne(item, createdEventId);
  };

  const allAttachmentsResolved =
    attachments.length > 0 && attachments.every((a) => attachmentStatus[a.id] === "success");

  useEffect(() => {
    if (createdEventId && attachments.length > 0 && allAttachmentsResolved) {
      navigate(`/events/${createdEventId}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allAttachmentsResolved, createdEventId]);

  // Roda a cada NOVA tentativa de envio (não a cada validação de onBlur) — depende só de
  // `submitCount` de propósito: o efeito fecha sobre o `errors` desta mesma renderização (já
  // pós-validação), então nunca fica com uma closure desatualizada como um `setTimeout` chamado
  // de dentro do handler de erro do `handleSubmit` ficaria (o erro que corrigimos aqui).
  useEffect(() => {
    if (formState.submitCount === 0) return;
    for (const field of FIELD_ORDER) {
      if (errors[field]) {
        setFocus(field);
        document.getElementById(field as string)?.scrollIntoView({ behavior: "smooth", block: "center" });
        break;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formState.submitCount]);

  const onSubmit = handleSubmit(
    (values) => {
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
        observations: observations
          .filter((o): o is ObservationInput & { obs_type: "text" | "link" } =>
            o.obs_type === "text" || o.obs_type === "link",
          )
          .map(({ obs_type, content, label }) => ({ obs_type, content, label })),
      };

      createEvent.mutate(payload, {
        onSuccess: (result) => {
          const eventId = result.event.id;
          setCreatedEventId(eventId);

          const pending: PendingAttachment[] = [
            ...paymentProofs.map((proof, i) => ({
              id: `payment-${i}`,
              kind: "payment" as const,
              proof,
            })),
            ...(contractFile
              ? [{ id: "contract", kind: "contract" as const, file: contractFile, signed: contractSigned }]
              : []),
            ...(hasReembolso && reembolsoDescription.trim() && reembolsoAmount > 0
              ? [
                  {
                    id: "reimbursement",
                    kind: "reimbursement" as const,
                    description: reembolsoDescription.trim(),
                    amount: reembolsoAmount,
                    file: reembolsoInvoiceFile,
                  },
                ]
              : []),
            ...observations
              .filter((o) => o.obs_type === "image" && o.file)
              .map((o, i) => ({
                id: `observation-${i}`,
                kind: "observation-image" as const,
                content: o.content,
                label: o.label,
                file: o.file as File,
              })),
          ];

          setAttachments(pending);
          setAttachmentStatus(Object.fromEntries(pending.map((p) => [p.id, "pending" as const])));

          if (pending.length === 0) {
            navigate(`/events/${eventId}`);
            return;
          }
          runUploads(pending, eventId);
        },
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
    },
    () => {
      setServerError("Existem campos obrigatórios não preenchidos. Verifique os destaques em vermelho.");
    },
  );

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

  if (createdEventId && attachments.length > 0) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <PageHeader title="Evento criado" className="mb-0" />
        <p className="text-sm text-muted">
          O evento foi criado. Finalizando o envio dos anexos antes de abrir a página do evento…
        </p>
        <PendingAttachmentsPanel
          items={attachments.map((a) => ({
            id: a.id,
            label:
              a.kind === "payment"
                ? `Comprovante: ${a.proof.file.name}`
                : a.kind === "contract"
                  ? `Contrato: ${a.file.name}`
                  : a.kind === "reimbursement"
                    ? "Reembolso"
                    : `Foto: ${a.file.name}`,
            status: attachmentStatus[a.id] ?? "pending",
          }))}
          onRetry={retryAttachment}
        />
        {attachments.some((a) => attachmentStatus[a.id] === "error") && (
          <Button onClick={() => navigate(`/events/${createdEventId}`)} variant="outline">
            Ver o evento mesmo assim
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link to="/agenda">‹ Agenda</Link>
        </Button>
        <Button asChild variant="ghost" size="sm">
          <Link to="/agenda">Cancelar</Link>
        </Button>
      </div>

      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
      >
        <PageHeader title="Novo evento" className="mb-0" />

        {serverError && (
          <div className="mt-4 rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
            {serverError}
          </div>
        )}

        <FormProvider {...methods}>
          <form ref={formRef} onSubmit={onSubmit} noValidate className="mt-4 space-y-4">
            <ClienteBlock
              clients={clients}
              onClientsChange={setClients}
              relationOptions={opts.client_relation_tipos}
              formResponse={formResponse}
              onFormResponseChange={setFormResponse}
            />

            <DadosEventoBlock
              hasReembolso={hasReembolso}
              onHasReembolsoChange={setHasReembolso}
              reembolsoDescription={reembolsoDescription}
              onReembolsoDescriptionChange={setReembolsoDescription}
              reembolsoAmount={reembolsoAmount}
              onReembolsoAmountChange={setReembolsoAmount}
              reembolsoInvoiceFile={reembolsoInvoiceFile}
              onReembolsoInvoiceFileChange={setReembolsoInvoiceFile}
            />

            {prefill.data?.orcamento_id && (
              <Card>
                <CardContent className="space-y-3 p-4">
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
                </CardContent>
              </Card>
            )}

            <ElencoBlock
              characters={characters}
              onCharactersChange={setCharacters}
              coordinatorTalentId={coordinatorTalentId}
              onCoordinatorTalentIdChange={setCoordinatorTalentId}
              figurinoSheets={opts.figurino_sheets}
              talents={opts.assignable_talents}
            />

            <ValoresBlock sellers={opts.sellers} />

            <PagamentoBlock proofs={paymentProofs} onProofsChange={setPaymentProofs} />

            <ContratoBlock
              contractFile={contractFile}
              onContractFileChange={setContractFile}
              contractSigned={contractSigned}
              onContractSignedChange={setContractSigned}
            />

            <ObservacoesBlock observations={observations} onObservationsChange={setObservations} />

            {serverError && (
              <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
                {serverError}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button asChild variant="outline">
                <Link to="/agenda">Cancelar</Link>
              </Button>
              <Button type="submit" loading={isSubmitting || createEvent.isPending}>
                {createEvent.isPending ? "Adicionando…" : "Adicionar à Agenda"}
              </Button>
            </div>
          </form>
        </FormProvider>
      </motion.div>
    </div>
  );
}
