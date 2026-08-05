import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion, useReducedMotion } from "framer-motion";
import { Button, PageHeader, Skeleton } from "@manto/ui";
import { ApiRequestError } from "@manto/api-client";
import { useEvent } from "../lib/agenda";
import { dataDeIsoLocal, horaDeIsoLocal } from "../lib/horaLocal";
import {
  eventSchema,
  DEFAULT_EVENT_FORM_VALUES,
  FIELD_ORDER,
  SERVER_FIELD_MAP,
  type EventFormValues,
} from "../lib/eventFormSchema";
import {
  useEventCreateOptions,
  useUpdateEvent,
  type CharacterInput,
  type ClientLinkInput,
  type EventUpdateInput,
  type ObservationInput,
  type PendingPaymentProof,
} from "../lib/eventCreate";
import { useAddPayment, useAddContract, useAddReimbursement } from "../lib/eventAttachments";
import { useAddImageObservation } from "../lib/observations";
import type { SelectedFormResponse } from "../components/FormResponsePicker";
import { ClienteBlock } from "../components/EventFormBlocks/ClienteBlock";
import { DadosEventoBlock } from "../components/EventFormBlocks/DadosEventoBlock";
import { ElencoBlock } from "../components/EventFormBlocks/ElencoBlock";
import { ValoresBlock } from "../components/EventFormBlocks/ValoresBlock";
import { PagamentoBlock } from "../components/EventFormBlocks/PagamentoBlock";
import { ContratoBlock } from "../components/EventFormBlocks/ContratoBlock";
import { ObservacoesBlock } from "../components/EventFormBlocks/ObservacoesBlock";
import {
  PendingAttachmentsPanel,
  type AttachmentUploadStatus,
} from "../components/PendingAttachmentsPanel";

type PendingAttachment =
  | { id: string; kind: "payment"; proof: PendingPaymentProof }
  | { id: string; kind: "contract"; file: File; signed: boolean }
  | { id: string; kind: "reimbursement"; description: string; amount: number; file: File | null }
  | { id: string; kind: "observation-image"; content: string; label: string; file: File };

export function EventEditPage() {
  const params = useParams<{ id: string }>();
  const eventId = Number(params.id);
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();

  const eventQuery = useEvent(eventId);
  const options = useEventCreateOptions();
  const updateEvent = useUpdateEvent(eventId);

  const [serverError, setServerError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
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

  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [attachmentStatus, setAttachmentStatus] = useState<Record<string, AttachmentUploadStatus>>({});
  const [uploadingAttachments, setUploadingAttachments] = useState(false);

  const methods = useForm<EventFormValues>({
    resolver: zodResolver(eventSchema),
    mode: "onBlur",
    defaultValues: DEFAULT_EVENT_FORM_VALUES,
  });
  const { handleSubmit, setError, setFocus, reset, formState } = methods;
  const { errors, isSubmitting } = formState;

  useEffect(() => {
    if (!eventQuery.data || loaded) return;
    const data = eventQuery.data;
    reset({
      ...DEFAULT_EVENT_FORM_VALUES,
      title: data.event.title,
      event_type: data.event.event_type || "",
      // `start_at`/`end_at` são horário de parede de São Paulo, não instante UTC — recortar a
      // string (ver `lib/horaLocal.ts`). Passar por `new Date(...).toISOString()` deslocava o
      // formulário em +3h e regravava o evento errado no banco e no Google Agenda.
      date: dataDeIsoLocal(data.event.start_at),
      start: horaDeIsoLocal(data.event.start_at),
      end: horaDeIsoLocal(data.event.end_at),
      location: data.event.location || "",
      // A descrição vai inteira no PATCH: hidratar vazio apagava a descrição do evento (e a do
      // Google Agenda junto) a cada salvamento.
      description: data.event.description || "",
      needs_rehearsal: data.event.needs_rehearsal,
      is_cortesia_permuta: data.venda?.is_cortesia_permuta ?? false,
      sale_value: data.venda?.sale_value ?? 0,
      sale_value_gross: data.venda?.sale_value_gross ?? 0,
      transport_value: data.venda?.transport_value ?? 0,
      acrescimo_value: data.venda?.acrescimo_value ?? 0,
      with_invoice: data.venda?.with_invoice ?? false,
      seller_id: data.venda?.seller_id ? String(data.venda.seller_id) : "",
      sale_date: data.venda?.sale_date || "",
      payment_method: data.venda?.payment_method || "",
      payment_installments: data.venda?.payment_installments
        ? String(data.venda.payment_installments)
        : "",
      payment_due_date: data.venda?.payment_due_date || "",
    });

    const roles = data.elenco ?? [];
    setCharacters(
      roles
        .filter((r) => r.role_type === "character")
        .map((r) => ({
          role_id: r.role_id,
          name: r.character_name,
          figurino_sheet_id: r.figurino_sheet_id,
          cache_value: r.cache_value ?? null,
          needs_makeup: r.needs_makeup,
          is_singer: r.is_singer,
          talent_id: r.talent?.id ?? null,
        })),
    );
    const coordinator = roles.find(
      (r) => r.role_type === "extra" && r.character_name === "Coordenador",
    );
    setCoordinatorTalentId(coordinator?.talent?.id ?? null);

    setClients(
      (data.venda?.clients ?? []).map((c) => ({
        client_id: c.client_id,
        relation: c.relation,
        name: c.name ?? "",
      })),
    );
    setFormResponse(data.venda?.form_response ?? null);

    setLoaded(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventQuery.data, loaded]);

  const addPayment = useAddPayment(eventId);
  const addContract = useAddContract(eventId);
  const addReimbursement = useAddReimbursement(eventId);
  const addImageObservation = useAddImageObservation(eventId);

  const uploadOne = async (item: PendingAttachment) => {
    setAttachmentStatus((s) => ({ ...s, [item.id]: "uploading" }));
    try {
      if (item.kind === "payment") {
        await addPayment.mutateAsync({ amount: item.proof.amount, file: item.proof.file });
      } else if (item.kind === "contract") {
        await addContract.mutateAsync({ file: item.file, is_signed: item.signed });
      } else if (item.kind === "reimbursement") {
        await addReimbursement.mutateAsync({
          description: item.description,
          amount: item.amount,
          file: item.file ?? undefined,
        });
      } else {
        await addImageObservation.mutateAsync({ file: item.file, label: item.label || undefined });
      }
      setAttachmentStatus((s) => ({ ...s, [item.id]: "success" }));
    } catch {
      setAttachmentStatus((s) => ({ ...s, [item.id]: "error" }));
    }
  };

  const retryAttachment = (id: string) => {
    const item = attachments.find((a) => a.id === id);
    if (item) uploadOne(item);
  };

  const allResolved = attachments.length > 0 && attachments.every((a) => attachmentStatus[a.id] === "success");

  useEffect(() => {
    if (uploadingAttachments && attachments.length > 0 && allResolved) {
      navigate(`/events/${eventId}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allResolved, uploadingAttachments]);

  // Ver EventCreatePage.tsx para o porquê deste efeito depender só de `submitCount` — evita a
  // closure desatualizada de `errors` que um `setTimeout` chamado de dentro do handler de erro
  // do `handleSubmit` teria.
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
      const payload: EventUpdateInput = {
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
        coordinator_talent_id: coordinatorTalentId,
        form_response_id: formResponse?.id ?? null,
        characters: characters.filter((c) => c.name.trim().length > 0),
        clients: clients.map(({ client_id, relation }) => ({ client_id, relation })),
      };

      updateEvent.mutate(payload, {
        onSuccess: () => {
          const pending: PendingAttachment[] = [
            ...paymentProofs.map((proof, i) => ({ id: `payment-${i}`, kind: "payment" as const, proof })),
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

          if (pending.length === 0) {
            navigate(`/events/${eventId}`);
            return;
          }
          setAttachments(pending);
          setAttachmentStatus(Object.fromEntries(pending.map((p) => [p.id, "pending" as const])));
          setUploadingAttachments(true);
          pending.forEach((item) => uploadOne(item));
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

  if (eventQuery.isLoading || options.isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (eventQuery.isError || !eventQuery.data || options.isError || !options.data) {
    return (
      <div className="mx-auto max-w-3xl p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o evento para edição.
        </div>
      </div>
    );
  }

  if (!eventQuery.data.flags.can_edit_core) {
    return (
      <div className="mx-auto max-w-3xl p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Você não tem permissão para editar este evento.
        </div>
      </div>
    );
  }

  const opts = options.data;
  const data = eventQuery.data;

  if (uploadingAttachments && attachments.length > 0) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <PageHeader title="Salvando anexos" className="mb-0" />
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
          <Button onClick={() => navigate(`/events/${eventId}`)} variant="outline">
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
          <Link to={`/events/${eventId}`}>‹ Evento</Link>
        </Button>
        <Button asChild variant="ghost" size="sm">
          <Link to={`/events/${eventId}`}>Cancelar</Link>
        </Button>
      </div>

      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
      >
        <PageHeader title={`Editar — ${data.event.title}`} className="mb-0" />

        {serverError && (
          <div className="mt-4 rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
            {serverError}
          </div>
        )}

        <FormProvider {...methods}>
          <form onSubmit={onSubmit} noValidate className="mt-4 space-y-4">
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
              existingReembolsoNote={
                (data.reembolsos?.items.length ?? 0) > 0 && (
                  <p className="mb-2 text-xs text-muted">
                    {data.reembolsos!.items.length} reembolso(s) já registrado(s) —{" "}
                    <Link to={`/events/${eventId}`} className="text-blue underline">
                      gerenciar na página do evento
                    </Link>
                    .
                  </p>
                )
              }
            />

            <ElencoBlock
              characters={characters}
              onCharactersChange={setCharacters}
              coordinatorTalentId={coordinatorTalentId}
              onCoordinatorTalentIdChange={setCoordinatorTalentId}
              figurinoSheets={opts.figurino_sheets}
              talents={opts.assignable_talents}
            />

            <ValoresBlock sellers={opts.sellers} />

            <PagamentoBlock
              proofs={paymentProofs}
              onProofsChange={setPaymentProofs}
              existingNote={
                (data.pagamentos?.items.length ?? 0) > 0 && (
                  <p className="mb-2 text-xs text-muted">
                    {data.pagamentos!.items.length} comprovante(s) já anexado(s) —{" "}
                    <Link to={`/events/${eventId}`} className="text-blue underline">
                      gerenciar na página do evento
                    </Link>
                    .
                  </p>
                )
              }
            />

            <ContratoBlock
              contractFile={contractFile}
              onContractFileChange={setContractFile}
              contractSigned={contractSigned}
              onContractSignedChange={setContractSigned}
              existingNote={
                (data.contratos?.length ?? 0) > 0 && (
                  <p className="mb-2 text-xs text-muted">
                    {data.contratos!.length} contrato(s) já anexado(s) —{" "}
                    <Link to={`/events/${eventId}`} className="text-blue underline">
                      gerenciar na página do evento
                    </Link>
                    .
                  </p>
                )
              }
            />

            <ObservacoesBlock
              observations={observations}
              onObservationsChange={setObservations}
              existingNote={
                (data.observations?.length ?? 0) > 0 && (
                  <p className="mb-2 text-xs text-muted">
                    {data.observations!.length} observação(ões) já registrada(s) —{" "}
                    <Link to={`/events/${eventId}`} className="text-blue underline">
                      ver na página do evento
                    </Link>
                    .
                  </p>
                )
              }
            />

            {serverError && (
              <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
                {serverError}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button asChild variant="outline">
                <Link to={`/events/${eventId}`}>Cancelar</Link>
              </Button>
              <Button type="submit" loading={isSubmitting || updateEvent.isPending}>
                {updateEvent.isPending ? "Salvando…" : "Salvar alterações"}
              </Button>
            </div>
          </form>
        </FormProvider>
      </motion.div>
    </div>
  );
}
