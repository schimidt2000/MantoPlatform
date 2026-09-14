import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { FormProvider, useForm, type UseFormSetValue } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion, useReducedMotion } from "framer-motion";
import { Button, PageHeader, Skeleton, Card, CardContent, formatShortDate } from "@manto/ui";
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
import {
  mensagemDaApi,
  useLinkEvent,
  useParaEvento,
  useUsarClienteDoEvento,
  type AlertaFormulario,
  type DivergenciaCliente,
  type ObservacaoRotulada,
  type ValoresDoFormulario,
} from "../lib/formulariosAdmin";
import { SeloDoFormulario } from "../components/EventFormBlocks/shared";
import { hojeYmd } from "../lib/horaLocal";
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

type ClienteDoCadastro = ClientLinkInput & { name: string };

/**
 * Pré-fill do formulário (feature 298): campo a campo com `setValue`, NUNCA um `reset` — que
 * zeraria a data da venda (hotfix 267b) e o vendedor. Valor, vendedor e título não vêm do
 * formulário.
 */
function preencherCamposDoFormulario(setValue: UseFormSetValue<EventFormValues>, v: ValoresDoFormulario) {
  const sujo = { shouldDirty: true } as const;
  if (v.date) setValue("date", v.date, sujo);
  if (v.start) setValue("start", v.start, sujo);
  if (v.end) setValue("end", v.end, sujo);
  if (v.location) setValue("location", v.location, sujo);
  if (v.event_type) setValue("event_type", v.event_type, sujo);
  if (v.payment_method) setValue("payment_method", v.payment_method, sujo);
  if (v.payment_installments) {
    setValue("payment_installments", String(v.payment_installments), sujo);
  }
}

/** As clientes do formulário somadas às já escolhidas, sem repetir a ficha. */
function somarClientesDoFormulario(
  atuais: ClienteDoCadastro[],
  doFormulario: NonNullable<ValoresDoFormulario["clients"]>,
  nomeDoContato: string | undefined,
): ClienteDoCadastro[] {
  const novas = doFormulario.filter((c) => !atuais.some((atual) => atual.client_id === c.client_id));
  if (novas.length === 0) return atuais;
  return [
    ...atuais,
    ...novas.map((c) => ({
      client_id: c.client_id,
      name: c.name ?? nomeDoContato ?? "Cliente",
      relation: c.relation ?? "Contratante",
    })),
  ];
}

/** Os personagens pedidos entram só com o elenco vazio: o do orçamento prevalece. */
function personagensDoFormulario(atuais: CharacterInput[], nomes: string[]): CharacterInput[] {
  if (atuais.length > 0 || nomes.length === 0) return atuais;
  return nomes.map((name) => ({
    role_id: null,
    name,
    figurino_sheet_id: null,
    cache_value: null,
    needs_makeup: false,
    is_singer: false,
    talent_id: null,
  }));
}

/**
 * Tema, aniversariante, espaço, briefing… viram observações rotuladas, nunca a descrição (que vai
 * para o Google Agenda).
 */
function somarObservacoesDoFormulario(atuais: ObservationInput[], notas: ObservacaoRotulada[]): ObservationInput[] {
  const comTexto = notas.filter((o) => o.text?.trim());
  if (comTexto.length === 0) return atuais;
  return [
    ...atuais,
    ...comTexto.map((o) => ({
      obs_type: "text" as const,
      content: o.text!.trim(),
      label: o.label ?? "",
      do_formulario: true,
    })),
  ];
}

export function EventCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const reduceMotion = useReducedMotion();
  const [searchParams] = useSearchParams();
  const orcamentoIdParam = searchParams.get("orcamento_id");
  const orcamentoId = orcamentoIdParam ? Number(orcamentoIdParam) : null;
  // Pré-preenchimento a partir de um formulário (Home "Criar evento", tela `/formularios`). A
  // feature 298 trocou o detalhe da resposta (que só dava a data e a cliente) pelo `para-evento`:
  // tudo o que a cliente escreveu, traduzido para o cadastro, com as marcas e os alertas. O RBAC
  // é o de quem cria evento (`_CAN_CREATE`: COMERCIAL e SUPERADMIN), o mesmo do `POST /api/events`.
  const formResponseIdParam = searchParams.get("form_response_id");
  const formResponseId = formResponseIdParam ? Number(formResponseIdParam) : null;

  const currentUser = useCurrentUser();
  const options = useEventCreateOptions();
  const prefill = useOrcamentoPrefill(orcamentoId);
  const paraEvento = useParaEvento(formResponseId);
  const ligar = useLinkEvent(formResponseId ?? 0);
  const usarCliente = useUsarClienteDoEvento();
  const createEvent = useCreateEvent();

  const [serverError, setServerError] = useState<string | null>(null);
  const [duracao, setDuracao] = useState("1");
  const [duracaoExtra, setDuracaoExtra] = useState("");
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
  // Feature 298: o que veio do formulário (marca "do formulário"), os alertas no campo e a data
  // suspeita, que pede conferência sem nunca desabilitar o Salvar.
  const [doFormulario, setDoFormulario] = useState<ReadonlySet<string>>(new Set());
  const [alertas, setAlertas] = useState<AlertaFormulario[]>([]);
  const [dataDoFormulario, setDataDoFormulario] = useState<string | null>(null);
  const [dataConfirmada, setDataConfirmada] = useState(false);
  const [vinculado, setVinculado] = useState<{
    eventId: number;
    divergencia: DivergenciaCliente;
  } | null>(null);
  const formularioAplicado = useRef<number | null>(null);

  const [createdEventId, setCreatedEventId] = useState<number | null>(null);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [attachmentStatus, setAttachmentStatus] = useState<Record<string, AttachmentUploadStatus>>({});

  const formRef = useRef<HTMLFormElement>(null);

  const methods = useForm<EventFormValues>({
    resolver: zodResolver(eventSchema),
    mode: "onBlur",
    // "Data da venda" nasce com hoje (hotfix 267b): o formulário clássico prefilhava e o React
    // não — 38 vendas de agosto entraram sem data e sumiram da Planilha de Pagamentos. O
    // servidor também assume hoje quando o campo vem vazio; aqui é para a pessoa VER a data.
    defaultValues: { ...DEFAULT_EVENT_FORM_VALUES, sale_date: hojeYmd() },
  });
  const { handleSubmit, setError, setValue, setFocus, clearErrors, watch, formState } = methods;
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
      (p.caches ?? [])
        .filter((c) => c.role_type === "character")
        .map((c) => ({
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

  // Pré-fill do formulário (feature 298) — as regras de cada parte estão nas funções acima.
  // Chaveado pelo id e guardado num ref: o StrictMode roda o efeito duas vezes, e observações e
  // personagens seriam somados em dobro.
  useEffect(() => {
    const p = paraEvento.data;
    const fr = p?.form_response;
    if (!p || !fr || formularioAplicado.current === fr.id) return;
    formularioAplicado.current = fr.id;
    const v = p.valores ?? {};
    setFormResponse({ id: fr.id, name: fr.contact_name ?? "", form_type: fr.form_type_label ?? "" });
    preencherCamposDoFormulario(setValue, v);
    setClients((atuais) => somarClientesDoFormulario(atuais, v.clients ?? [], fr.contact_name));
    setCharacters((atuais) => personagensDoFormulario(atuais, v.characters ?? []));
    setObservations((atuais) => somarObservacoesDoFormulario(atuais, p.observacoes ?? []));
    setDoFormulario(new Set(p.origem ?? []));
    setAlertas(p.alertas ?? []);
    setDataDoFormulario(v.date ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paraEvento.data?.form_response?.id]);

  const dataAtual = watch("date");
  const alertaDaData = alertas.find((a) => a.campo === "date" && a.motivo === "data_suspeita");
  // A conferência só vale enquanto a data é a que veio do formulário: trocou, está conferida.
  const pedeConferirData = Boolean(alertaDaData) && dataAtual === dataDoFormulario;
  const eventosDaCliente = paraEvento.data?.eventos_da_cliente ?? [];

  /** "Ligar a este evento": a cliente já tem a festa na agenda sem formulário (FR-013). */
  const ligarAoEvento = (eventId: number) =>
    ligar.mutate(eventId, {
      onSuccess: (resultado) => {
        if (resultado.divergencia_cliente) {
          setVinculado({ eventId, divergencia: resultado.divergencia_cliente });
          return;
        }
        navigate(`/events/${eventId}`);
      },
    });

  // Default do vendedor: o próprio usuário, se ele estiver na lista de vendedores.
  useEffect(() => {
    if (!options.data || !currentUser.data) return;
    const isSeller = options.data.sellers.some((s) => s.id === currentUser.data!.id);
    if (isSeller) setValue("seller_id", String(currentUser.data.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.data, currentUser.data]);

  useEffect(() => {
    const custom = prefill.data?.duracao_custom;
    if (custom && custom > 4) selectDuracaoExtra(String(custom));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill.data?.duracao_custom]);

  const selectDuracao = (dur: "1" | "2" | "3" | "4") => {
    setDuracao(dur);
    setDuracaoExtra("");
    if (!prefill.data) return;
    const total = prefill.data[`total_${dur}h` as "total_1h"] ?? 0;
    setValue("sale_value_gross", total);
    setValue("sale_value", total);
  };

  /**
   * Duração acima de 4h (feature 236): o evento pode declarar a duração REAL — antes o
   * formulário só oferecia 1–4h e um evento de 6 horas nascia com cachês (e teto) errados.
   * O preço de referência usa o total_custom do orçamento quando a duração bate; senão, a
   * mesma régua linear da calculadora (total de 4h ÷ 4 × horas) — só sugestão, editável.
   */
  const selectDuracaoExtra = (raw: string) => {
    setDuracaoExtra(raw);
    const horas = Number(raw);
    if (!Number.isInteger(horas) || horas < 5) return;
    setDuracao(String(horas));
    if (!prefill.data) return;
    const total4 = prefill.data.total_4h ?? 0;
    const total =
      prefill.data.duracao_custom === horas && prefill.data.total_custom
        ? prefill.data.total_custom
        : Math.round((total4 / 4) * horas * 100) / 100;
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
      // Data suspeita do formulário (feature 298): o Salvar nunca fica desabilitado. Salvar sem
      // trocar a data nem marcar "A data está certa" aponta o campo com a explicação, e o efeito
      // de foco (chaveado em `submitCount`) leva até ele.
      if (pedeConferirData && !dataConfirmada) {
        setError("date", {
          message: `${alertaDaData?.mensagem ?? "A data informada parece errada."} Troque a data ou marque “A data está certa”.`,
        });
        return;
      }
      const payload: EventCreateInput = {
        title: values.title,
        event_type: values.event_type,
        date: values.date,
        start: values.start,
        end: values.end,
        location: values.location,
        description: values.description,
        // "SHOW sempre pede ensaio" é regra do servidor (feature 239): `_create_event_row`
        // liga o flag sozinho, e o cliente manda só o que o usuário marcou.
        needs_rehearsal: values.needs_rehearsal,
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

        {formResponseId != null && paraEvento.isLoading && <Skeleton className="mt-4 h-14 w-full" />}
        {paraEvento.isError && (
          <div className="mt-4 rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
            Não deu para trazer os dados do formulário:{" "}
            {mensagemDaApi(paraEvento.error, "tente abrir de novo.")}
          </div>
        )}
        {paraEvento.data?.form_response && (
          <div className="mt-4 rounded-md bg-accent-soft px-4 py-3 text-sm text-ink" role="status">
            Preenchido a partir do formulário de{" "}
            <strong>{paraEvento.data.form_response.contact_name ?? "cliente"}</strong> — confira os
            campos com o selo <SeloDoFormulario />. Valor, vendedor e título ficam com você.
          </div>
        )}
        {eventosDaCliente.length > 0 && !vinculado && (
          <div className="mt-3 space-y-2 rounded-md bg-gold-50 px-4 py-3 text-sm text-ink">
            <p>
              Esta cliente já tem evento na agenda sem formulário. Se for a mesma festa, ligue em vez
              de criar outro:
            </p>
            <ul className="space-y-1.5">
              {eventosDaCliente.map((ev) => (
                <li key={ev.event_id} className="flex flex-wrap items-center justify-between gap-2">
                  <span className="min-w-0">
                    {ev.titulo ?? "Evento"} ·{" "}
                    <span className="tabular-nums">{formatShortDate(ev.data ?? null)}</span>
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    loading={ligar.isPending && ligar.variables === ev.event_id}
                    onClick={() => ligarAoEvento(ev.event_id)}
                  >
                    Ligar a este evento
                  </Button>
                </li>
              ))}
            </ul>
            {ligar.isError && (
              <p role="alert" className="text-xs text-red">
                {mensagemDaApi(ligar.error, "Não foi possível ligar. Tente novamente.")}
              </p>
            )}
          </div>
        )}
        {vinculado && (
          <div role="status" className="mt-3 space-y-2 rounded-md bg-gold-50 px-4 py-3 text-sm text-ink">
            {usarCliente.isSuccess ? (
              <p>
                Formulário ligado, agora com a cliente do evento (
                <strong>{vinculado.divergencia.evento.nome ?? "sem nome"}</strong>).
              </p>
            ) : (
              <p>
                Formulário ligado. A cliente do formulário (
                <strong>{vinculado.divergencia.formulario.nome ?? "sem nome"}</strong>) não é a
                cliente do evento (<strong>{vinculado.divergencia.evento.nome ?? "sem nome"}</strong>)
                — o evento não foi alterado.
              </p>
            )}
            {/* Mesma saída da Home e de `/formularios` (FR-015): a comercial escolhe, nada troca sozinho. */}
            <div className="flex flex-wrap gap-2">
              {!usarCliente.isSuccess && formResponseId !== null && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  loading={usarCliente.isPending}
                  onClick={() => usarCliente.mutate(formResponseId)}
                >
                  Usar a cliente do evento neste formulário
                </Button>
              )}
              <Button type="button" size="sm" onClick={() => navigate(`/events/${vinculado.eventId}`)}>
                Abrir o evento
              </Button>
            </div>
            {usarCliente.isError && (
              <p role="alert" className="text-xs text-red">
                {mensagemDaApi(usarCliente.error, "Não foi possível trocar a cliente. Tente novamente.")}
              </p>
            )}
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
              doFormulario={doFormulario}
              alertas={alertas}
              cadastroRapidoInicial={paraEvento.data?.valores?.quick_create_client ?? undefined}
            />

            <DadosEventoBlock
              doFormulario={doFormulario}
              alertas={alertas}
              confirmacaoDaData={
                pedeConferirData
                  ? {
                      marcada: dataConfirmada,
                      onChange: (marcada) => {
                        setDataConfirmada(marcada);
                        if (marcada) clearErrors("date");
                      },
                    }
                  : undefined
              }
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
                    <label
                      className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                        duracaoExtra && duracao === duracaoExtra
                          ? "border-accent bg-accent-soft text-ink"
                          : "border-line bg-panel text-ink"
                      }`}
                    >
                      Outra (h):
                      <input
                        type="number"
                        min={5}
                        className="w-16 rounded border border-line bg-panel px-1 py-0.5 text-sm text-ink"
                        value={duracaoExtra}
                        onChange={(e) => selectDuracaoExtra(e.target.value)}
                        aria-label="Outra duração em horas"
                      />
                      {duracaoExtra && duracao === duracaoExtra && prefill.data && (
                        <span className="text-xs text-muted">
                          R$ {formatBRL(
                            prefill.data.duracao_custom === Number(duracaoExtra) && prefill.data.total_custom
                              ? prefill.data.total_custom
                              : Math.round(((prefill.data.total_4h ?? 0) / 4) * Number(duracaoExtra) * 100) / 100,
                          )}
                        </span>
                      )}
                    </label>
                  </div>
                </CardContent>
              </Card>
            )}

            {doFormulario.has("characters") && (
              <p className="-mb-2 text-xs text-muted">
                Personagens sugeridos a partir do formulário <SeloDoFormulario /> — confira.
              </p>
            )}
            <ElencoBlock
              characters={characters}
              onCharactersChange={setCharacters}
              coordinatorTalentId={coordinatorTalentId}
              onCoordinatorTalentIdChange={setCoordinatorTalentId}
              talents={opts.assignable_talents}
            />

            <ValoresBlock sellers={opts.sellers} />

            <PagamentoBlock
              proofs={paymentProofs}
              onProofsChange={setPaymentProofs}
              doFormulario={doFormulario}
              alertas={alertas}
            />

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
