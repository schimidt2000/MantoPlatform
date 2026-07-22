import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@manto/api-client";

export interface RoleOption {
  id: number;
  name: string;
}

export interface UserSalary {
  amount: number;
  payment_type: "semanal" | "quinzenal" | "comissao";
  start_date: string;
  notes: string;
}

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  has_access: boolean;
  is_active: boolean;
  receives_commission: boolean;
  pix_key: string;
  pix_key_type: string;
  role_names: string[];
  role_ids: number[];
  salary: UserSalary | null;
}

export interface AdminUsersListResponse {
  items: AdminUser[];
  all_roles: RoleOption[];
}

export interface SalaryHistoryEntry {
  id: number;
  amount: number;
  payment_type: string;
  start_date: string;
  end_date: string | null;
  notes: string;
}

export interface AdminUserDetail extends AdminUser {
  salary_history: SalaryHistoryEntry[];
  all_roles: RoleOption[];
}

/** Lista de usuários com o salário vigente de cada um (feature 167). */
export function useAdminUsers() {
  return useQuery<AdminUsersListResponse>({
    queryKey: ["admin-users"],
    queryFn: () => apiFetch<AdminUsersListResponse>("/api/admin/users"),
  });
}

/** Ficha de um usuário, com o histórico completo de salário (feature 167). */
export function useAdminUser(id: number) {
  return useQuery<AdminUserDetail>({
    queryKey: ["admin-users", id],
    queryFn: () => apiFetch<AdminUserDetail>(`/api/admin/users/${id}`),
    enabled: Number.isFinite(id),
  });
}

export interface SalaryInput {
  amount: string;
  payment_type: string;
  start_date?: string;
  notes?: string;
}

export interface CreateAdminUserInput {
  user_type: "access" | "payment_only";
  name: string;
  email?: string;
  temp_password?: string;
  role_ids?: number[];
  pix_key?: string;
  pix_key_type?: string;
  salary?: SalaryInput;
}

/** Cria um usuário com acesso ou só-pagamento (feature 167). */
export function useCreateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAdminUserInput) =>
      apiFetch<AdminUser>("/api/admin/users", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export interface UpdateAdminUserIdentityInput {
  name: string;
  email?: string;
  is_active: boolean;
  receives_commission: boolean;
  role_ids?: number[];
}

/** Atualiza identidade/papéis/status/comissão de um usuário (feature 167). */
export function useUpdateAdminUserIdentity(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateAdminUserIdentityInput) =>
      apiFetch<AdminUser>(`/api/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users", id] });
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

/** Atualiza a chave PIX de um usuário (feature 167). */
export function useUpdatePix(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { pix_key?: string; pix_key_type?: string }) =>
      apiFetch<AdminUser>(`/api/admin/users/${id}/pix`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users", id] });
    },
  });
}

/** Registra um novo salário para o usuário, encerrando o vigente (feature 167). */
export function useAddSalary(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SalaryInput) =>
      apiFetch(`/api/admin/users/${id}/salary`, { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users", id] });
    },
  });
}

/** Concede acesso ao sistema a uma pessoa cadastrada só para pagamento (feature 167). */
export function useGrantAccess(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { email: string; temp_password: string }) =>
      apiFetch<AdminUser>(`/api/admin/users/${id}/grant-access`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users", id] });
    },
  });
}

/** Reseta a senha de um usuário (feature 167). */
export function useResetPassword(id: number) {
  return useMutation({
    mutationFn: (temp_password: string) =>
      apiFetch<{ ok: boolean }>(`/api/admin/users/${id}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ temp_password }),
      }),
  });
}

/** Exclui um usuário sem histórico financeiro vinculado (feature 167). */
export function useDeleteAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/admin/users/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}
