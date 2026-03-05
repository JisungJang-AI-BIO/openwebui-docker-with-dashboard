import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MessagesSquare, MessageSquare, Bot, ThumbsUp, Wrench, Puzzle, Sparkles } from "lucide-react";
import StatCard from "@/components/StatCard";
import DailyChart from "@/components/DailyChart";
import TabGroup from "@/components/TabGroup";
import WorkspaceRankingTable from "@/components/WorkspaceRankingTable";
import DeveloperRankingTable from "@/components/DeveloperRankingTable";
import UserRankingTable from "@/components/UserRankingTable";
import GroupRankingTable from "@/components/GroupRankingTable";
import ToolRankingTable from "@/components/ToolRankingTable";
import FunctionRankingTable from "@/components/FunctionRankingTable";
import SkillRankingTable from "@/components/SkillRankingTable";
import RequirePackages from "@/components/RequirePackages";
import IssueReports from "@/components/IssueReports";
import MockAuthBanner from "@/components/MockAuthBanner";
import {
  fetchOverview, fetchDailyStats, fetchWorkspaceRanking,
  fetchDeveloperRanking, fetchUserRanking, fetchGroupRanking,
  fetchToolRanking, fetchFunctionRanking, fetchSkillRanking,
  type OverviewStats, type DailyStat,
  type WorkspaceRanking, type DeveloperRanking, type UserRanking, type GroupRanking,
  type ToolRanking, type FunctionRanking, type SkillRanking,
} from "@/lib/api";

const PAGE_SIZE = 20;

const TABS = [
  { id: "usage", label: "Usage Rankings" },
  { id: "assets", label: "Asset Registry" },
  { id: "requests", label: "Requests & Reports" },
];

function kstDate(offsetDays: number): string {
  const d = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Seoul" }));
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export default function Dashboard() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceRanking[]>([]);
  const [developers, setDevelopers] = useState<DeveloperRanking[]>([]);
  const [users, setUsers] = useState<UserRanking[]>([]);
  const [groups, setGroups] = useState<GroupRanking[]>([]);
  const [tools, setTools] = useState<ToolRanking[]>([]);
  const [functions, setFunctions] = useState<FunctionRanking[]>([]);
  const [skills, setSkills] = useState<SkillRanking[]>([]);
  const [mockUser, setMockUser] = useState(() => localStorage.getItem("mockUser") || "jisung.jang");
  const [searchParams, setSearchParams] = useSearchParams();
  const dateFrom = searchParams.get("from") || kstDate(-7);
  const dateTo = searchParams.get("to") || kstDate(-1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("usage");

  const [wsOffset, setWsOffset] = useState(0);
  const [wsTotal, setWsTotal] = useState(0);
  const [devOffset, setDevOffset] = useState(0);
  const [devTotal, setDevTotal] = useState(0);
  const [usrOffset, setUsrOffset] = useState(0);
  const [usrTotal, setUsrTotal] = useState(0);
  const [grpOffset, setGrpOffset] = useState(0);
  const [grpTotal, setGrpTotal] = useState(0);
  const [toolOffset, setToolOffset] = useState(0);
  const [toolTotal, setToolTotal] = useState(0);
  const [fnOffset, setFnOffset] = useState(0);
  const [fnTotal, setFnTotal] = useState(0);
  const [skillOffset, setSkillOffset] = useState(0);
  const [skillTotal, setSkillTotal] = useState(0);

  useEffect(() => {
    Promise.all([
      fetchOverview().then(setOverview),
      fetchDailyStats(dateFrom, dateTo).then(setDaily),
      fetchWorkspaceRanking(0, PAGE_SIZE).then((res) => { setWorkspaces(res.items); setWsTotal(res.total); }),
      fetchDeveloperRanking(0, PAGE_SIZE).then((res) => { setDevelopers(res.items); setDevTotal(res.total); }),
      fetchUserRanking(0, PAGE_SIZE).then((res) => { setUsers(res.items); setUsrTotal(res.total); }),
      fetchGroupRanking(0, PAGE_SIZE).then((res) => { setGroups(res.items); setGrpTotal(res.total); }),
      fetchToolRanking(0, PAGE_SIZE).then((res) => { setTools(res.items); setToolTotal(res.total); }),
      fetchFunctionRanking(0, PAGE_SIZE).then((res) => { setFunctions(res.items); setFnTotal(res.total); }),
      fetchSkillRanking(0, PAGE_SIZE).then((res) => { setSkills(res.items); setSkillTotal(res.total); }),
    ])
      .catch((err) => setError(err?.message || "Failed to load dashboard data."))
      .finally(() => setLoading(false));
  }, []);

  const handleDateChange = (from: string, to: string) => {
    setSearchParams({ from, to });
    fetchDailyStats(from, to)
      .then(setDaily)
      .catch((err) => setError(err?.message || "Failed to load daily stats."));
  };

  const handleWsPage = (newOffset: number) => {
    setWsOffset(newOffset);
    fetchWorkspaceRanking(newOffset, PAGE_SIZE).then((res) => { setWorkspaces(res.items); setWsTotal(res.total); });
  };
  const handleDevPage = (newOffset: number) => {
    setDevOffset(newOffset);
    fetchDeveloperRanking(newOffset, PAGE_SIZE).then((res) => { setDevelopers(res.items); setDevTotal(res.total); });
  };
  const handleUsrPage = (newOffset: number) => {
    setUsrOffset(newOffset);
    fetchUserRanking(newOffset, PAGE_SIZE).then((res) => { setUsers(res.items); setUsrTotal(res.total); });
  };
  const handleGrpPage = (newOffset: number) => {
    setGrpOffset(newOffset);
    fetchGroupRanking(newOffset, PAGE_SIZE).then((res) => { setGroups(res.items); setGrpTotal(res.total); });
  };
  const handleToolPage = (newOffset: number) => {
    setToolOffset(newOffset);
    fetchToolRanking(newOffset, PAGE_SIZE).then((res) => { setTools(res.items); setToolTotal(res.total); });
  };
  const handleFnPage = (newOffset: number) => {
    setFnOffset(newOffset);
    fetchFunctionRanking(newOffset, PAGE_SIZE).then((res) => { setFunctions(res.items); setFnTotal(res.total); });
  };
  const handleSkillPage = (newOffset: number) => {
    setSkillOffset(newOffset);
    fetchSkillRanking(newOffset, PAGE_SIZE).then((res) => { setSkills(res.items); setSkillTotal(res.total); });
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-lg text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <p className="text-lg text-red-400">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats + Chart (always visible) */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard title="Total Chats" value={overview?.total_chats ?? 0} icon={MessagesSquare} />
        <StatCard title="Total Messages" value={overview?.total_messages ?? 0} icon={MessageSquare} />
        <StatCard title="Workspaces" value={overview?.total_models ?? 0} icon={Bot} />
        <StatCard title="Feedbacks" value={overview?.total_feedbacks ?? 0} icon={ThumbsUp} />
        <StatCard title="Tools" value={overview?.total_tools ?? 0} icon={Wrench} />
        <StatCard title="Functions" value={overview?.total_functions ?? 0} icon={Puzzle} />
        <StatCard title="Skills" value={overview?.total_skills ?? 0} icon={Sparkles} />
      </div>
      <DailyChart data={daily} dateFrom={dateFrom} dateTo={dateTo} onDateChange={handleDateChange} />

      {/* Tab navigation */}
      <TabGroup tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab: Usage Rankings */}
      {activeTab === "usage" && (
        <div className="space-y-6">
          <WorkspaceRankingTable data={workspaces} total={wsTotal} offset={wsOffset} limit={PAGE_SIZE} onPageChange={handleWsPage} />
          <DeveloperRankingTable data={developers} total={devTotal} offset={devOffset} limit={PAGE_SIZE} onPageChange={handleDevPage} />
          <UserRankingTable data={users} total={usrTotal} offset={usrOffset} limit={PAGE_SIZE} onPageChange={handleUsrPage} />
          <GroupRankingTable data={groups} total={grpTotal} offset={grpOffset} limit={PAGE_SIZE} onPageChange={handleGrpPage} />
        </div>
      )}

      {/* Tab: Asset Registry */}
      {activeTab === "assets" && (
        <div className="space-y-6">
          <ToolRankingTable data={tools} total={toolTotal} offset={toolOffset} limit={PAGE_SIZE} onPageChange={handleToolPage} />
          <FunctionRankingTable data={functions} total={fnTotal} offset={fnOffset} limit={PAGE_SIZE} onPageChange={handleFnPage} />
          <SkillRankingTable data={skills} total={skillTotal} offset={skillOffset} limit={PAGE_SIZE} onPageChange={handleSkillPage} />
        </div>
      )}

      {/* Tab: Requests & Reports */}
      {activeTab === "requests" && (
        <div className="space-y-6">
          <RequirePackages currentUser={mockUser} />
          <IssueReports currentUser={mockUser} />
        </div>
      )}

      <MockAuthBanner user={mockUser} onChangeUser={(u) => { setMockUser(u); localStorage.setItem("mockUser", u); }} />
    </div>
  );
}
