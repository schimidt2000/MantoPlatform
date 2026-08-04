import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { CalendarPlus, Trash2 } from "lucide-react";
import {
  AvatarThumb,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Combobox,
  Input,
  PageHeader,
  Skeleton,
  type ComboboxOption,
} from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import { MoneyInput, formatBRL } from "@manto/money";
import {
  apiMoneyToNumber,
  numberToApiMoney,
  useGerarSlots,
  useRemoverSlot,
  useSetVirtualCampaignAcervo,
  useSetVirtualCampaignStatus,
  useUpdateVirtualCampaign,
  useVirtualCampaign,
  VIRTUAL_CAMPAIGN_STATUS_LABELS,
  VIRTUAL_CAMPAIGN_STATUS_TONES,
  type VirtualCampaignStatus,
  type VirtualFaqItem,
} from "../lib/virtuais";

/**
 * Edição de uma campanha da Loja de Interações Virtuais (feature 205, US1).
 *
 * Reúne num lugar só o que define a oferta: textos públicos, os três preços, o estoque de horários
 * e as peças do Acervo 3D liberadas.
 *
 * Duas regras da constituição visíveis aqui:
 * - **dinheiro só por `@manto/money`** — `MoneyInput` para digitar, `formatBRL` para exibir;
 *   nenhuma máscara própria (Princípio IX);
 * - **erro da API nunca limpa o formulário** — a mensagem aparece no campo e o que foi digitado
 *   permanece (Princípio V).
 */

interface FieldErrors {
  [field: string]: string;
}

/** Extrai o mapa campo→mensagem do envelope de erro da API. */
function extractFieldErrors(error: unknown): FieldErrors {
  if (error && typeof error === "object" && "fields" in error) {
    const fields = (error as { fields?: unknown }).fields;
    if (fields && typeof fields === "object") return fields as FieldErrors;
  }
  return {};
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-[12px] text-red">{message}</p>;
}

export function VirtuaisCampanhaFormPage() {
  const { id } = useParams<{ id: string }>();
  const campaignId = Number(id);
  const reduceMotion = useReducedMotion();

  const { data: campaign, isLoading } = useVirtualCampaign(
    Number.isFinite(campaignId) ? campaignId : null,
  );
  const updateCampaign = useUpdateVirtualCampaign(campaignId);
  const setStatus = useSetVirtualCampaignStatus(campaignId);
  const gerarSlots = useGerarSlots(campaignId);
  const removerSlot = useRemoverSlot(campaignId);
  const setAcervo = useSetVirtualCampaignAcervo(campaignId);

  const [title, setTitle] = useState("");
  const [introHtml, setIntroHtml] = useState("");
  const [toleranceTerms, setToleranceTerms] = useState("");
  const [whatsappPhone, setWhatsappPhone] = useState("");
  const [priceLive, setPriceLive] = useState(0);
  const [priceRecorded, setPriceRecorded] = useState(0);
  const [priceGift, setPriceGift] = useState(0);
  const [recordedCapacity, setRecordedCapacity] = useState(0);
  const [deliveryDays, setDeliveryDays] = useState(7);
  const [faq, setFaq] = useState<VirtualFaqItem[]>([]);
  const [acervoIds, setAcervoIds] = useState<number[]>([]);
  const [errors, setErrors] = useState<FieldErrors>({});

  const [slotDate, setSlotDate] = useState("");
  const [slotStart, setSlotStart] = useState("14:00");
  const [slotEnd, setSlotEnd] = useState("18:00");
  const [slotFeedback, setSlotFeedback] = useState<string | null>(null);

  // Carrega o estado do formulário a partir do servidor uma vez que a campanha chega.
  useEffect(() => {
    if (!campaign) return;
    setTitle(campaign.title);
    setIntroHtml(campaign.intro_html ?? "");
    setToleranceTerms(campaign.tolerance_terms ?? "");
    setWhatsappPhone(campaign.whatsapp_phone ?? "");
    setPriceLive(apiMoneyToNumber(campaign.price_live));
    setPriceRecorded(apiMoneyToNumber(campaign.price_recorded));
    setPriceGift(apiMoneyToNumber(campaign.price_gift));
    setRecordedCapacity(campaign.recorded_capacity);
    setDeliveryDays(campaign.recorded_delivery_days);
    setFaq(campaign.faq);
    setAcervoIds(campaign.acervo_item_ids);
  }, [campaign]);

  const handleSave = () => {
    setErrors({});
    updateCampaign.mutate(
      {
        title,
        intro_html: introHtml,
        tolerance_terms: toleranceTerms,
        whatsapp_phone: whatsappPhone,
        price_live: numberToApiMoney(priceLive),
        price_recorded: numberToApiMoney(priceRecorded),
        price_gift: numberToApiMoney(priceGift),
        recorded_capacity: recordedCapacity,
        recorded_delivery_days: deliveryDays,
        faq,
      },
      { onError: (error) => setErrors(extractFieldErrors(error)) },
    );
  };

  const handleStatus = (status: VirtualCampaignStatus) => {
    setErrors({});
    setStatus.mutate(status, { onError: (error) => setErrors(extractFieldErrors(error)) });
  };

  const handleGerarSlots = () => {
    setSlotFeedback(null);
    setErrors({});
    gerarSlots.mutate(
      { date: slotDate, start: slotStart, end: slotEnd },
      {
        onSuccess: (result) =>
          setSlotFeedback(
            `${result.created} horário(s) criado(s)` +
              (result.skipped > 0 ? ` · ${result.skipped} já existiam` : ""),
          ),
        onError: (error) => setErrors(extractFieldErrors(error)),
      },
    );
  };

  if (isLoading || !campaign) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  // Só as peças ainda não liberadas viram opção — repetir seleção não faz sentido.
  const giftOptions: ComboboxOption[] = campaign.available_gift_items
    .filter((item) => !acervoIds.includes(item.id))
    .map((item) => ({
      value: String(item.id),
      label: item.name,
      imageUrl: assetUrl(item.photo_url),
      imageShape: "square" as const,
    }));

  return (
    <motion.div
      className="space-y-4"
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <PageHeader
        title={campaign.title}
        subtitle={campaign.character?.name ?? undefined}
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={VIRTUAL_CAMPAIGN_STATUS_TONES[campaign.status]}>
              {VIRTUAL_CAMPAIGN_STATUS_LABELS[campaign.status]}
            </Badge>
            {campaign.status !== "publicada" ? (
              <Button
                variant="outline"
                loading={setStatus.isPending}
                onClick={() => handleStatus("publicada")}
              >
                Publicar
              </Button>
            ) : (
              <Button
                variant="outline"
                loading={setStatus.isPending}
                onClick={() => handleStatus("pausada")}
              >
                Pausar
              </Button>
            )}
            <Button loading={updateCampaign.isPending} onClick={handleSave}>
              Salvar
            </Button>
          </div>
        }
      />

      {/* A publicação valida a oferta inteira; quando falta algo, o motivo aparece aqui. */}
      {Object.keys(errors).length > 0 && (
        <div className="rounded-lg border border-red/30 bg-red-soft p-3 text-sm text-red">
          {Object.values(errors)[0]}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Conteúdo público</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-[12px] font-medium text-muted" htmlFor="title">
                Título
              </label>
              <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
              <FieldError message={errors.title} />
            </div>
            <div>
              <label className="text-[12px] font-medium text-muted" htmlFor="intro">
                Texto de apresentação
              </label>
              <textarea
                id="intro"
                className="min-h-24 w-full rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink"
                value={introHtml}
                onChange={(e) => setIntroHtml(e.target.value)}
              />
            </div>
            <div>
              <label className="text-[12px] font-medium text-muted" htmlFor="tolerance">
                Termos de tolerância
              </label>
              <textarea
                id="tolerance"
                className="min-h-20 w-full rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink"
                value={toleranceTerms}
                onChange={(e) => setToleranceTerms(e.target.value)}
              />
              <FieldError message={errors.tolerance_terms} />
            </div>
            <div>
              <label className="text-[12px] font-medium text-muted" htmlFor="whatsapp">
                WhatsApp de atendimento
              </label>
              <Input
                id="whatsapp"
                value={whatsappPhone}
                onChange={(e) => setWhatsappPhone(e.target.value)}
                placeholder="+55 11 99999-8888"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Preços e estoque</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="price-live">
                  Chamada ao vivo
                </label>
                <MoneyInput
                  id="price-live"
                  className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink"
                  value={priceLive}
                  onValueChange={setPriceLive}
                />
                <FieldError message={errors.price_live} />
              </div>
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="price-recorded">
                  Vídeo gravado
                </label>
                <MoneyInput
                  id="price-recorded"
                  className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink"
                  value={priceRecorded}
                  onValueChange={setPriceRecorded}
                />
                <FieldError message={errors.price_recorded} />
              </div>
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="price-gift">
                  Presente 3D
                </label>
                <MoneyInput
                  id="price-gift"
                  className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink"
                  value={priceGift}
                  onValueChange={setPriceGift}
                />
                <FieldError message={errors.price_gift} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="capacity">
                  Capacidade de vídeos
                </label>
                <Input
                  id="capacity"
                  type="number"
                  min={0}
                  value={recordedCapacity}
                  onChange={(e) => setRecordedCapacity(Number(e.target.value))}
                />
                <p className="mt-1 text-[11px] text-muted">
                  {campaign.recorded_used} de {campaign.recorded_capacity_total} já vendidos
                </p>
              </div>
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="delivery">
                  Prazo de entrega (dias)
                </label>
                <Input
                  id="delivery"
                  type="number"
                  min={1}
                  value={deliveryDays}
                  onChange={(e) => setDeliveryDays(Number(e.target.value))}
                />
                <FieldError message={errors.recorded_delivery_days} />
              </div>
            </div>

            <p className="text-[11px] text-muted">
              Faturado até agora: R$ {formatBRL(apiMoneyToNumber(campaign.revenue))} em{" "}
              {campaign.sold_count} venda(s).
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Estoque de horários</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="slot-date">
                  Data
                </label>
                <Input
                  id="slot-date"
                  type="date"
                  value={slotDate}
                  onChange={(e) => setSlotDate(e.target.value)}
                />
                <FieldError message={errors.date} />
              </div>
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="slot-start">
                  Início
                </label>
                <Input
                  id="slot-start"
                  type="time"
                  value={slotStart}
                  onChange={(e) => setSlotStart(e.target.value)}
                />
              </div>
              <div>
                <label className="text-[12px] font-medium text-muted" htmlFor="slot-end">
                  Fim
                </label>
                <Input
                  id="slot-end"
                  type="time"
                  value={slotEnd}
                  onChange={(e) => setSlotEnd(e.target.value)}
                />
                <FieldError message={errors.end} />
              </div>
            </div>

            <Button
              variant="outline"
              loading={gerarSlots.isPending}
              disabled={!slotDate}
              onClick={handleGerarSlots}
            >
              <CalendarPlus className="size-4" />
              Gerar horários de 10 min
            </Button>

            {slotFeedback && <p className="text-[12px] text-green">{slotFeedback}</p>}

            <p className="text-[11px] text-muted">
              {campaign.slots_available} disponível(is) de {campaign.slots_total} horário(s).
              Reexecutar a mesma janela não duplica nada.
            </p>

            {campaign.slots.length > 0 && (
              <div className="max-h-48 space-y-1 overflow-y-auto">
                {campaign.slots.map((slot) => (
                  <div
                    key={slot.id}
                    className="flex items-center justify-between rounded border border-line px-2 py-1 text-[12px]"
                  >
                    <span className="text-ink">
                      {new Date(slot.start_at).toLocaleString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge tone={slot.status === "livre" ? "neutral" : "gold"}>
                        {slot.status}
                      </Badge>
                      {slot.status === "livre" && (
                        <button
                          type="button"
                          aria-label="Remover horário"
                          className="text-muted hover:text-red"
                          onClick={() => removerSlot.mutate(slot.id)}
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Presentes 3D liberados</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {/* Seleção visual: miniatura quadrada ao lado do nome (Princípio XII.2). */}
            <Combobox
              options={giftOptions}
              value={null}
              onChange={(value) => {
                if (!value) return;
                const itemId = Number(value);
                if (acervoIds.includes(itemId)) return;
                const novos = [...acervoIds, itemId];
                setAcervoIds(novos);
                setAcervo.mutate(novos);
              }}
              placeholder="Buscar peça do Acervo 3D…"
              emptyMessage="Nenhuma peça encontrada"
              disabled={setAcervo.isPending}
            />

            {campaign.gift_items.length === 0 ? (
              <p className="text-[12px] text-muted">
                Nenhuma peça liberada — a etapa de presente não aparece no checkout.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {campaign.gift_items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-2 rounded-lg border border-line px-2 py-1"
                  >
                    <AvatarThumb
                      src={assetUrl(item.photo_url)}
                      name={item.name}
                      shape="square"
                      size="sm"
                      fallbackIcon="🎁"
                    />
                    <span className="text-[12px] text-ink">{item.name}</span>
                    <button
                      type="button"
                      aria-label={`Remover ${item.name}`}
                      className="text-muted hover:text-red"
                      onClick={() => {
                        const novos = acervoIds.filter((existing) => existing !== item.id);
                        setAcervoIds(novos);
                        setAcervo.mutate(novos);
                      }}
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <p className="text-[11px] text-muted">
              Valor adicional do presente: R$ {formatBRL(priceGift)}.
            </p>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
