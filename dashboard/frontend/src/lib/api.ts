import axios from "axios";

// Production: frontend and backend share the same nginx origin (empty baseURL).
// Development: set VITE_API_BASE_URL=http://localhost:8005 in .env.local
const baseURL = import.meta.env.VITE_API_BASE_URL || "";

const api = axios.create({ baseURL });

export interface OverviewStats {
  total_chats: number;
  total_messages: number;
  total_models: number;
  total_feedbacks: number;
  total_tools: number;
  total_functions: number;
  total_skills: number;
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

export interface UserRanking {
  user_id: string;
  user_name: string;
  email: string;
  chat_count: number;
  message_count: number;
  workspace_count: number;
  total_feedbacks: number;
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

export interface ToolRanking {
  id: string;
  name: string;
  creator_name: string;
  creator_email: string;
  created_at: string;
  updated_at: string;
}

export interface FunctionRanking {
  id: string;
  name: string;
  type: string;
  is_active: boolean;
  is_global: boolean;
  creator_name: string;
  creator_email: string;
  created_at: string;
  updated_at: string;
}

export interface SkillRanking {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  creator_name: string;
  creator_email: string;
  created_at: string;
  updated_at: string;
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

export const fetchUserRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<UserRanking>>(`/api/v1/stats/user-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchGroupRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<GroupRanking>>(`/api/v1/stats/group-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchToolRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<ToolRanking>>(`/api/v1/stats/tool-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchFunctionRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<FunctionRanking>>(`/api/v1/stats/function-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchSkillRanking = (offset = 0, limit = 20) =>
  api.get<PaginatedResponse<SkillRanking>>(`/api/v1/stats/skill-ranking?offset=${offset}&limit=${limit}`).then((r) => r.data);

export const fetchPackages = () =>
  api.get<PaginatedResponse<PythonPackage>>("/api/v1/packages?limit=200").then((r) => r.data.items);

export const addPackage = (packageName: string, authUser: string) =>
  api.post<PythonPackage>("/api/v1/packages", { package_name: packageName }, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const deletePackage = (id: number, authUser: string) =>
  api.delete(`/api/v1/packages/${id}`, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const updatePackageStatus = (id: number, status: string, authUser: string, note?: string) =>
  api.patch(`/api/v1/packages/${id}/status`, { status, status_note: note }, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export interface IssueReport {
  id: number;
  title: string;
  description: string;
  category: "bug" | "feature" | "question" | "other";
  reported_by: string;
  is_anonymous: boolean;
  status: "open" | "in_progress" | "resolved" | "rejected" | "wontfix";
  admin_note: string | null;
  created_at: string;
  updated_at: string;
}

export const fetchReports = () =>
  api.get<PaginatedResponse<IssueReport>>("/api/v1/reports?limit=200").then((r) => r.data.items);

export const createReport = (data: { title: string; description: string; category: string; is_anonymous: boolean }, authUser: string) =>
  api.post<IssueReport>("/api/v1/reports", data, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const updateReportStatus = (id: number, status: string, authUser: string, adminNote?: string) =>
  api.patch(`/api/v1/reports/${id}/status`, { status, admin_note: adminNote }, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const deleteReport = (id: number, authUser: string) =>
  api.delete(`/api/v1/reports/${id}`, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export interface AuthMe {
  user: string;
  is_admin: boolean;
}

export const fetchAuthMe = (authUser: string) =>
  api.get<AuthMe>("/api/v1/auth/me", { headers: { "X-Auth-User": authUser } }).then((r) => r.data);
