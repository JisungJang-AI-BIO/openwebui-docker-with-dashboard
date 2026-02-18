import axios from "axios";

const BACKEND_PORT = 8005;
const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}`;

const api = axios.create({ baseURL });

export interface OverviewStats {
  total_chats: number;
  total_messages: number;
  total_models: number;
  total_feedbacks: number;
}

export interface DailyStat {
  date: string;
  chat_count: number;
  message_count: number;
  user_count: number;
}

export interface WorkspaceRanking {
  id: string;
  name: string;
  developer_email: string;
  user_count: number;
  chat_count: number;
  message_count: number;
  positive: number;
  negative: number;
}

export interface DeveloperRanking {
  user_id: string;
  user_name: string;
  email: string;
  workspace_count: number;
  total_users: number;
  total_chats: number;
  total_messages: number;
  total_positive: number;
  total_negative: number;
}

export interface GroupRanking {
  group_id: string;
  group_name: string;
  member_count: number;
  total_chats: number;
  total_messages: number;
  total_feedbacks: number;
  chats_per_member: number;
  messages_per_member: number;
}

export interface PythonPackage {
  id: number;
  package_name: string;
  added_by: string;
  added_at: string;
  status: "pending" | "installed" | "rejected" | "uninstalled";
  status_note: string | null;
}

export interface PaginatedResponse<T> {
  total: number;
  offset: number;
  limit: number;
  items: T[];
}

export const fetchOverview = () =>
  api.get<OverviewStats>("/api/v1/stats/overview").then((r) => r.data);

export const fetchDailyStats = (from?: string, to?: string) => {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  return api
    .get<DailyStat[]>(`/api/v1/stats/daily?${params.toString()}`)
    .then((r) => r.data);
};

export const fetchWorkspaceRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<WorkspaceRanking>>(`/api/v1/stats/workspace-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchDeveloperRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<DeveloperRanking>>(`/api/v1/stats/developer-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchGroupRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<GroupRanking>>(`/api/v1/stats/group-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchPackages = () =>
  api.get<PaginatedResponse<PythonPackage>>("/api/v1/packages?limit=200").then((r) => r.data.items);

export const addPackage = (packageName: string, authUser: string) =>
  api.post<PythonPackage>("/api/v1/packages", { package_name: packageName }, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const deletePackage = (id: number, authUser: string) =>
  api.delete(`/api/v1/packages/${id}`, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const updatePackageStatus = (id: number, status: string, authUser: string, note?: string) =>
  api.patch(`/api/v1/packages/${id}/status`, { status, status_note: note }, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export interface AuthMe {
  user: string;
  is_admin: boolean;
}

export const fetchAuthMe = (authUser: string) =>
  api.get<AuthMe>("/api/v1/auth/me", { headers: { "X-Auth-User": authUser } }).then((r) => r.data);
