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

export interface ModelStat {
  model: string;
  chat_count: number;
  avg_response_length: number;
}

export interface RecentChat {
  id: string;
  title: string;
  models: string[];
  message_count: number;
  created_at: string;
  updated_at: string;
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

export const fetchModelStats = () =>
  api.get<ModelStat[]>("/api/stats/models").then((r) => r.data);

export const fetchRecentChats = (limit = 20) =>
  api.get<RecentChat[]>(`/api/chats/recent?limit=${limit}`).then((r) => r.data);

export const fetchFeedbackSummary = () =>
  api.get<FeedbackSummary>("/api/feedbacks/summary").then((r) => r.data);
