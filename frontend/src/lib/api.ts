import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8005",
});

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

export const fetchOverview = () =>
  api.get<OverviewStats>("/api/stats/overview").then((r) => r.data);

export const fetchDailyStats = (from?: string, to?: string) => {
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  return api
    .get<DailyStat[]>(`/api/stats/daily?${params.toString()}`)
    .then((r) => r.data);
};

export const fetchWorkspaceRanking = () =>
  api.get<WorkspaceRanking[]>("/api/stats/workspace-ranking").then((r) => r.data);

export const fetchDeveloperRanking = () =>
  api.get<DeveloperRanking[]>("/api/stats/developer-ranking").then((r) => r.data);

export const fetchGroupRanking = () =>
  api.get<GroupRanking[]>("/api/stats/group-ranking").then((r) => r.data);

export const fetchPackages = () =>
  api.get<PythonPackage[]>("/api/packages").then((r) => r.data);

export const addPackage = (packageName: string, authUser: string) =>
  api.post<PythonPackage>("/api/packages", { package_name: packageName }, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const deletePackage = (id: number, authUser: string) =>
  api.delete(`/api/packages/${id}`, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);

export const updatePackageStatus = (id: number, status: string, authUser: string, note?: string) =>
  api.patch(`/api/packages/${id}/status`, { status, status_note: note }, { headers: { "X-Auth-User": authUser } }).then((r) => r.data);
