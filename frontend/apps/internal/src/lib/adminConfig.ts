import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface AdminSettings {
  logo_path: string;
  default_commission_rate: number | null;
  educamanto_seller_id: number | null;
  tax_rate: number | null;
  fator_r_threshold: number | null;
  manto_address: string;
  departure_margin_minutes: number | null;
  google_maps_api_key: string;
  email_notifications_enabled: boolean;
  whatsapp_form_number: string;
  /** Link de review no Google mostrado à cliente que dá 5 estrelas; vazio = default. */
  google_review_url: string;
  release_date: string | null;
}

export function useAdminSettings() {
  return useQuery<AdminSettings>({
    queryKey: ["admin-settings"],
    queryFn: () => apiFetch<AdminSettings>("/api/admin/settings"),
  });
}

export function useUpdateAdminSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Partial<AdminSettings> & { logo?: File }) => {
      if (input.logo) {
        const form = new FormData();
        Object.entries(input).forEach(([key, value]) => {
          if (value === undefined || value === null) return;
          form.set(key, value instanceof File ? value : String(value));
        });
        return apiFetch("/api/admin/settings", { method: "PATCH", body: form });
      }
      return apiFetch("/api/admin/settings", { method: "PATCH", body: JSON.stringify(input) });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-settings"] });
    },
  });
}

export interface AuditLogEntry {
  id: number;
  actor_name: string;
  actor_role: string;
  entity_type: string;
  entity_id: number | null;
  entity_name: string;
  action: string;
  detail: string;
  created_at: string;
}

export interface AdminLogsResponse {
  items: AuditLogEntry[];
  page: number;
  pages: number;
  total: number;
  entity_types: string[];
}

export function useAdminLogs(entityType: string, actor: string, page: number) {
  const params = new URLSearchParams({ page: String(page) });
  if (entityType) params.set("entity_type", entityType);
  if (actor) params.set("actor", actor);
  return useQuery<AdminLogsResponse>({
    queryKey: ["admin-logs", entityType, actor, page],
    queryFn: () => apiFetch<AdminLogsResponse>(`/api/admin/logs?${params.toString()}`),
  });
}

export interface DesempenhoItem {
  name: string;
  count: number;
  total?: number;
}

export interface AdminDesempenho {
  month: string;
  casting: DesempenhoItem[];
  figurino: DesempenhoItem[];
  vendas: DesempenhoItem[];
  totals: { casting: number; figurino: number; vendas: number; valor: number };
}

export function useAdminDesempenho(month: string) {
  return useQuery<AdminDesempenho>({
    queryKey: ["admin-desempenho", month],
    queryFn: () => apiFetch<AdminDesempenho>(`/api/admin/desempenho?month=${month}`),
  });
}

export interface SyncMonthInfo {
  ym: string;
  age_min: number | null;
  fresh: boolean;
  count: number;
}

export interface AdminSyncStatus {
  months: SyncMonthInfo[];
  auto_sync_age_min: number | null;
  recent_logs: { id: number; actor_name: string; detail: string; created_at: string }[];
}

export function useAdminSyncStatus() {
  return useQuery<AdminSyncStatus>({
    queryKey: ["admin-sync-status"],
    queryFn: () => apiFetch<AdminSyncStatus>("/api/admin/sync-status"),
  });
}

export interface SyncRunResult {
  results: { ym: string; ok: boolean; count?: number; removed?: number; err?: string }[];
  message: string;
}

export function useRunSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (action: "sync_now" | "cleanup_past") =>
      apiFetch<SyncRunResult>("/api/admin/sync/run", {
        method: "POST",
        body: JSON.stringify({ action }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-sync-status"] });
    },
  });
}

export function usePortalAnnouncement() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ sent: number; failed: number }>("/api/admin/portal-announcement", {
        method: "POST",
      }),
  });
}

export interface MigrationStatus {
  running: boolean;
  done: boolean;
  total: number;
  processed: number;
  started_at: string | null;
  finished_at: string | null;
  [key: string]: unknown;
}

export interface MigrarArquivosStatus {
  pending_count: number;
  pending: { talent_id: number; name: string; field: string }[];
  status: MigrationStatus;
}

export function useMigrarArquivosStatus() {
  return useQuery<MigrarArquivosStatus>({
    queryKey: ["admin-migrar-arquivos-status"],
    queryFn: () => apiFetch<MigrarArquivosStatus>("/api/admin/migrar-arquivos/status"),
    refetchInterval: (query) => (query.state.data?.status.running ? 3000 : false),
  });
}

export function useStartMigrarArquivos() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ started: boolean }>("/api/admin/migrar-arquivos/start", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-migrar-arquivos-status"] });
    },
  });
}

export interface ImportarCatalogoStatus {
  total_items: number;
  status: MigrationStatus;
}

export function useImportarCatalogoStatus() {
  return useQuery<ImportarCatalogoStatus>({
    queryKey: ["admin-importar-catalogo-status"],
    queryFn: () => apiFetch<ImportarCatalogoStatus>("/api/admin/importar-catalogo/status"),
    refetchInterval: (query) => (query.state.data?.status.running ? 3000 : false),
  });
}

export function useStartImportarCatalogo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ started: boolean }>("/api/admin/importar-catalogo/start", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-importar-catalogo-status"] });
    },
  });
}
