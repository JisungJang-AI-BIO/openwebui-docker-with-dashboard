import { useEffect, useState } from "react";
import { MessageSquare, Bot, Hash, Star } from "lucide-react";
import StatCard from "@/components/StatCard";
import DailyChart from "@/components/DailyChart";
import ModelBarChart from "@/components/ModelBarChart";
import WorkspaceRankingTable from "@/components/WorkspaceRankingTable";
import DeveloperRankingTable from "@/components/DeveloperRankingTable";
import GroupRankingTable from "@/components/GroupRankingTable";
import FeedbackSummary from "@/components/FeedbackSummary";
import {
  fetchOverview, fetchDailyStats, fetchWorkspaceRanking,
  fetchDeveloperRanking, fetchGroupRanking, fetchFeedbackSummary,
  type OverviewStats, type DailyStat,
  type WorkspaceRanking, type DeveloperRanking, type GroupRanking,
  type FeedbackSummary as FeedbackSummaryType,
} from "@/lib/api";

function todayKST(): string {
  return new Date(Date.now() + 9 * 3600_000).toISOString().slice(0, 10);
}

function daysAgoKST(days: number): string {
  return new Date(Date.now() + 9 * 3600_000 - days * 86400_000).toISOString().slice(0, 10);
}

export default function Dashboard() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceRanking[]>([]);
  const [developers, setDevelopers] = useState<DeveloperRanking[]>([]);
  const [groups, setGroups] = useState<GroupRanking[]>([]);
  const [feedback, setFeedback] = useState<FeedbackSummaryType | null>(null);
  const [dateFrom, setDateFrom] = useState(daysAgoKST(29));
  const [dateTo, setDateTo] = useState(todayKST());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchOverview().then(setOverview),
      fetchDailyStats(dateFrom, dateTo).then(setDaily),
      fetchWorkspaceRanking().then(setWorkspaces),
      fetchDeveloperRanking().then(setDevelopers),
      fetchGroupRanking().then(setGroups),
      fetchFeedbackSummary().then(setFeedback),
    ]).finally(() => setLoading(false));
  }, []);

  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
    fetchDailyStats(from, to).then(setDaily);
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-lg text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Chats" value={overview?.total_chats ?? 0} icon={MessageSquare} />
        <StatCard title="Total Messages" value={overview?.total_messages ?? 0} icon={Hash} />
        <StatCard title="Workspaces" value={overview?.total_models ?? 0} icon={Bot} />
        <StatCard title="Feedbacks" value={overview?.total_feedbacks ?? 0} icon={Star} />
      </div>
      <DailyChart data={daily} dateFrom={dateFrom} dateTo={dateTo} onDateChange={handleDateChange} />
      <WorkspaceRankingTable data={workspaces} />
      <ModelBarChart data={workspaces} />
      <DeveloperRankingTable data={developers} />
      <GroupRankingTable data={groups} />
      <FeedbackSummary data={feedback} />
    </div>
  );
}
