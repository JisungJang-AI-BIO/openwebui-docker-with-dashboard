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
}

export interface WorkspaceRanking {
  id: string;
  name: string;
  chat_count: number;
  message_count: number;
  positive: number;
  negative: number;
}

export interface FeedbackItem {
  id: string;
  model_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface FeedbackSummary {
  positive: number;
  negative: number;
  recent: FeedbackItem[];
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

export const fetchFeedbackSummary = () =>
  api.get<FeedbackSummary>("/api/feedbacks/summary").then((r) => r.data);
