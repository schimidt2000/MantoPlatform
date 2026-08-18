import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";
import type { Event3DGift } from "./impressoes3d";
import type { AvisoFalho } from "./virtuais";

/** Resumo de um evento na agenda (data-model.md: EventoResumo). Sem dado financeiro. */
export interface EventoResumo {
  id: number;
  title: string;
  event_type: string;
  start_at: string | null;
  end_at: string | null;
  location: string | null;
  characters: string[];
  is_satellite: boolean;
  group_name: string | null;
  confirmed: boolean;
}

export interface AgendaMes {
  ym: string;
  events: EventoResumo[];
  by_day: Record<string, number[]>;
}

export interface AgendaDia {
  day: string;
  events: EventoResumo[];
}

/** Agenda de um mês (`ym` = "YYYY-MM"). */
export function useAgenda(ym: string) {
  return useQuery<AgendaMes>({
    queryKey: ["agenda", ym],
    queryFn: () => apiFetch<AgendaMes>(`/api/agenda?ym=${encodeURIComponent(ym)}`),
  });
}

/** Eventos de um dia (`date` = "YYYY-MM-DD"). */
export function useAgendaDia(date: string) {
  return useQuery<AgendaDia>({
    queryKey: ["agenda-dia", date],
    queryFn: () => apiFetch<AgendaDia>(`/api/agenda/day/${date}`),
    enabled: Boolean(date),
  });
}

/** Um ensaio agendado de um show, no painel de Ensaio do detalhe do evento. */
export interface EnsaioDoEvento {
  id: number;
  start_at: string | null;
  end_at: string | null;
  description: string | null;
  location: string | null;
}

/** Resultado da busca — resumo + cliente (nome/telefone `null` para papéis sem vendas). */
export interface EventoBusca extends EventoResumo {
  client_name: string | null;
  client_phone_display: string | null;
}

export interface AgendaBusca {
  q: string;
  items: EventoBusca[];
  total: number;
  limit: number;
}

/**
 * Busca textual de eventos (título, cliente, telefone). Só dispara com 2+ caracteres;
 * `keepPreviousData` evita a lista piscar a cada tecla (espelho de `useClientSearch`).
 */
export function useAgendaSearch(q: string) {
  return useQuery<AgendaBusca>({
    queryKey: ["agenda-search", q],
    queryFn: () => apiFetch<AgendaBusca>(`/api/agenda/search?q=${encodeURIComponent(q)}`),
    enabled: q.trim().length >= 2,
    placeholderData: keepPreviousData,
  });
}

// ── Detalhe do evento (leitura) ──────────────────────────────────────────────
// Blocos financeiros são OPCIONAIS: só vêm no JSON conforme o papel (RBAC no servidor).

/** Talento escalado, já com o que o card de casting/figurino mostra (feature 190). */
export interface RoleTalent {
  id: number;
  name: string;
  artistic_name: string | null;
  /** Rosto do talento (feature 215) — mesmo caminho que a busca de casting usa. */
  photo_url: string | null;
  first_name: string;
  whatsapp: string | null;
  size_top: string | null;
  size_bottom: string | null;
  shoe_size: string | null;
  height_cm: number | null;
  /**
   * Documento e nascimento do "Exportar elenco". Opcionais de propósito: o servidor só manda
   * para Casting/Comercial/Superadmin (RBAC em `_serialize_talent`) — para os outros papéis a
   * chave nem existe no JSON.
   */
  birth_date?: string | null;
  cpf?: string | null;
  rg?: string | null;
  doc_photo_path?: string | null;
}

/** Estado da agenda do talento na janela do evento (feature 190). */
export interface RoleAvailability {
  status: "free" | "same_day" | "conflict";
  info: string;
}

/** Status de pagamento do cachê de um cargo (mesma lista aceita pelo servidor). */
export type PaymentStatus = "nao_pago" | "pago" | "no_banco" | "fora_do_banco";

/**
 * Nome da vaga "presença" do som — quem vai fisicamente ao evento (feature 239).
 *
 * Não confundir com a vaga "Técnico de Som" (a do PIX, do Nivaldo), que essa sim tem cachê.
 * A de presença nunca tem valor, é designada no painel de Ensaio e aparece no casting apenas
 * como leitura. Constante única para o nome não virar literal espalhado pelas telas — o
 * servidor manda `is_presence` em cada cargo, e isto aqui é só a retaguarda para payload antigo.
 */
export const PRESENCA_CHARACTER = "Técnico de Som (Presença)";

export interface RoleItem {
  role_id: number;
  character_name: string;
  /** "character" = personagem do evento; "extra" = equipe de apoio (coordenador, técnico…). */
  role_type: string;
  talent: RoleTalent | null;
  figurino_done: boolean;
  invite_status: string | null;
  dismissed: boolean;
  cache_value?: number | null; // só para casting/superadmin
  travel_cache?: number | null; // idem
  cache_cap?: number | null; // só para superadmin (feature 239)
  /**
   * Feature 239 — a conta do teto em valores ("Ator cara-limpa: base 2h R$ 300 + noturno
   * R$ 50 = R$ 350"), gravada na criação quando o evento nasceu de um orçamento. Só chega
   * para superadmin; `null` quando o papel foi criado sem orçamento vinculado.
   */
  cache_cap_note?: string | null;
  /** Feature 239 — este integrante leva um veículo no evento fora de SP ("carrinho"). */
  does_transport?: boolean;
  /** Parcela de UM veículo do orçamento; o mesmo valor para todos os papéis do evento. */
  transporte_valor?: number | null;
  /**
   * Teto já calculado pelo servidor: `max(cache_cap, cachê salvo)` + parcela do veículo quando
   * o carrinho está marcado. A tela não refaz essa conta — a regra mora no servidor.
   */
  cache_cap_efetivo?: number | null;
  figurino_sheet_id: number | null;
  figurino_sheet_name: string | null;
  figurino_done_at: string | null;
  /**
   * Manutenção aberta na ficha deste personagem (feature 225b), ou `null`.
   * `impede_uso` significa que a peça não pode ir para o evento até o conserto — é o que traz
   * um defeito relatado numa festa para a hora de separar o figurino da próxima.
   */
  figurino_manutencao: {
    abertas: number;
    impede_uso: boolean;
    titulos: string[];
  } | null;
  assigned_at: string | null;
  payment_status: PaymentStatus;
  availability: RoleAvailability | null;
  needs_makeup: boolean;
  is_singer: boolean;
  /**
   * Feature 239 — é a vaga "Técnico de Som (Presença)": somente leitura no casting (sem cachê,
   * sem convite, sem pagamento). O servidor nem manda os campos de dinheiro dela.
   */
  is_presence?: boolean;
}

/** Estimativa de trajeto Manto → local do evento (cache do Google Maps). */
export interface EventTravel {
  time_minutes: number | null;
  distance_km: number | null;
  is_outside_sp: boolean | null;
  suggested_departure: string | null;
  maps_url: string | null;
}

export interface EventRatingItem {
  id: number;
  talent_name: string;
  score: number;
  comment: string | null;
  submitted_at: string | null;
  sub_ratings: {
    category: string;
    subject_name: string | null;
    score: number;
    comment: string | null;
  }[];
}

export interface ClientFeedbackItem {
  id: number;
  score: number;
  comment: string | null;
  client_name: string | null;
  tags: string[];
  submitted_at: string | null;
}

export interface EventMaterial {
  id: number;
  material_type: "file" | "link";
  label: string | null;
  url: string | null;
  file_path: string | null;
  created_at: string | null;
}

export interface EventGasto {
  id: number;
  description: string;
  category: string;
  amount: number | null;
  expense_date: string | null;
  receipt_path: string | null;
}

export interface EventAcrescimo {
  id: number;
  label: string;
  tipo: string;
  is_percent: boolean;
  value: number | null;
  amount_brl: number | null;
  is_bv: boolean;
  bv_recipient: string | null;
  bv_payment_status: string;
}

/** Trechos fixos das mensagens de WhatsApp copiadas pela tela (feature 083). */
export interface EventMensagens {
  characters: string;
  date_line: string;
  location: string;
  cobranca_amount: string;
  cobranca_due: string;
  reembolso_lines: string[];
}

export interface EventoDetalhe {
  event: {
    id: number;
    title: string;
    event_type: string;
    start_at: string | null;
    end_at: string | null;
    location: string | null;
    confirmed: boolean;
    confirmed_by: string | null;
    /** Preenchido = evento cancelado (feature 224): sai da agenda e de toda métrica. */
    cancelled_at: string | null;
    cancelled_by: string | null;
    cancellation_reason: string | null;
    /** Solicitação de exclusão do Comercial ainda não decidida pelo Superadmin. */
    deletion_request: {
      requested_at: string;
      requested_by: string | null;
      reason: string | null;
    } | null;
    is_satellite: boolean;
    group_name: string | null;
    characters: string[];
    is_ensaio: boolean;
    // Logística (feature 149)
    makeup_time: string | null;
    makeup_location: string | null;
    departure_time: string | null;
    departure_location: string | null;
    needs_rehearsal: boolean;
    // Detalhe do evento (feature 190)
    description: string | null;
    google_html_link: string | null;
    travel: EventTravel;
  };
  flags: Record<string, boolean>;
  /**
   * Ensaios agendados do show (pós-206) — presente em eventos não-ENSAIO. As ações de
   * escrita são gated por `flags.show_ensaio` (Ensaio/Casting/Superadmin).
   */
  ensaios?: EnsaioDoEvento[];
  /** Vaga "Técnico de Som (Presença)" — `null` quando o evento não tem a vaga. */
  presenca?: { role_id: number; talent_id: number | null; talent_name: string | null } | null;
  /** Só em eventos ENSAIO: show pai do ensaio (`null` = órfão, feature 057/063). */
  ensaio_pai?: { id: number; title: string } | null;
  /**
   * Log de atividades — o servidor só serializa a chave para SUPERADMIN (real, sem
   * impersonação); ausente para os demais papéis, mesmo padrão de `kpi?`/`venda?`.
   */
  logs?: { ts: string; actor_name: string; actor_role: string; message: string }[];
  elenco?: RoleItem[];
  /**
   * Resumo de maquiador para o badge do Casting (feature 239, decisão 17). `precisa` = algum
   * personagem com `needs_makeup`; `fechado` = existe vaga extra com nome ~"maquiad" e talento
   * atribuído — mesmo critério do `has_makeup_role` legado.
   */
  maquiagem?: { precisa: boolean; fechado: boolean };
  materiais?: EventMaterial[];
  /**
   * Presentes 3D do evento (feature 200) — só vem no payload quando o evento é do tipo SHOW;
   * a chave ausente é o sinal para não renderizar a seção.
   */
  presentes_3d?: Event3DGift[];
  /**
   * Venda da Loja de Interações Virtuais (feature 205) — só vem quando o evento é do tipo
   * `VIRTUAL`; a chave ausente é o sinal para não renderizar a seção. Traz a ficha que a família
   * preencheu e o acesso à sala, que é o que o talento escalado precisa para executar.
   */
  pedido_virtual?: {
    order_nsu: string;
    modality: "ao_vivo" | "gravado";
    child_name: string;
    child_age: number;
    behavior_notes: string | null;
    contact_phone_display: string | null;
    contact_email: string;
    delivery_address: string | null;
    /** Link da sala do Meet — distinto do link do evento no Google Calendar. */
    meet_url: string | null;
    meet_pending: boolean;
    campaign_title: string | null;
    /** Id do pedido — endereça as ações de reenvio de aviso e de regeração de sala. */
    id: number;
    /** Avisos automáticos que não chegaram à família (FR-039c). */
    avisos_falhos: AvisoFalho[];
    /** A política de retry da sala se esgotou: ninguém mais vai tentar sozinho (FR-056a). */
    meet_retry_esgotado: boolean;
    meet_attempts: number;
  };
  ratings?: { items: EventRatingItem[]; average: number | null; count: number };
  client_feedbacks?: ClientFeedbackItem[];
  gastos?: EventGasto[];
  acrescimos?: EventAcrescimo[];
  mensagens?: EventMensagens;
  reembolsos_pendentes_total?: number | null;
  feedback_link_pendente?: boolean;
  observations?: {
    id: number;
    obs_type: string;
    content: string | null;
    label: string | null;
    image_url?: string | null;
  }[];
  venda?: {
    sale_value: number | null;
    sale_value_gross: number | null;
    transport_value: number | null;
    acrescimo_value: number | null;
    is_cortesia_permuta: boolean;
    with_invoice: boolean;
    seller: string | null;
    seller_id: number | null;
    sale_date: string | null;
    commission_rate: number | null;
    payment_method: string | null;
    payment_installments: number | null;
    payment_due_date: string | null;
    // feature 239 — só vem preenchido quando o usuário consegue abrir o orçamento
    // (superadmin, ou comercial dono do orçamento); demais papéis recebem null.
    orcamento_history_id: number | null;
    clients: { client_id: number; name: string | null; relation: string }[];
    form_response: { id: number; name: string; form_type: string } | null;
  };
  contratos?: { id: number; file_path: string; is_signed: boolean; created_at: string | null }[];
  notas_fiscais?: {
    id: number;
    amount: number | null;
    issue_date: string | null;
    status: string;
    file: string | null;
  }[];
  cobranca?: { outstanding: number | null; due: string | null; enabled: boolean };
  kpi?: {
    sale_value: number | null;
    cost: number | null;
    expenses_total: number | null;
    bv_total: number | null;
    commission: number | null;
    lucro: number | null;
    rate: number;
    group_size: number;
    seller: string | null;
  };
  pagamentos?: {
    items: { id: number; amount: number | null; file_path: string; created_at: string | null }[];
    received_total: number | null;
  };
  reembolsos?: {
    items: {
      id: number;
      description: string;
      amount: number | null;
      invoice_file_path: string | null;
      is_collected: boolean;
      collected_amount: number | null;
      receipt_file_path: string | null;
      created_at: string | null;
    }[];
    pendentes_total: number | null;
  };
}

/** Detalhe de um evento (leitura). */
export function useEvent(id: number) {
  return useQuery<EventoDetalhe>({
    queryKey: ["event", id],
    queryFn: () => apiFetch<EventoDetalhe>(`/api/events/${id}`),
    enabled: Number.isFinite(id),
  });
}
