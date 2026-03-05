import { useState, useEffect } from "react";
import {
  X, Plus, Loader2, Bug, Lightbulb, HelpCircle, MoreHorizontal,
  CheckCircle2, Clock, XCircle, ChevronDown, ChevronUp, EyeOff,
} from "lucide-react";
import { fetchReports, fetchAuthMe, createReport, deleteReport, updateReportStatus, type IssueReport } from "@/lib/api";
import { useToast } from "./Toast";

interface IssueReportsProps {
  currentUser: string;
}

const CATEGORY_CONFIG = {
  bug:      { icon: Bug,            color: "text-rose-400",    bg: "bg-rose-400/10",    label: "Bug" },
  feature:  { icon: Lightbulb,      color: "text-violet-400",  bg: "bg-violet-400/10",  label: "Feature" },
  question: { icon: HelpCircle,     color: "text-sky-400",     bg: "bg-sky-400/10",     label: "Question" },
  other:    { icon: MoreHorizontal, color: "text-zinc-400",    bg: "bg-zinc-400/10",    label: "Other" },
} as const;

const STATUS_CONFIG = {
  open:        { icon: Clock,        color: "text-amber-400",   bg: "bg-amber-400/10",   label: "Open" },
  in_progress: { icon: Loader2,      color: "text-blue-400",    bg: "bg-blue-400/10",    label: "In Progress" },
  resolved:    { icon: CheckCircle2, color: "text-emerald-400", bg: "bg-emerald-400/10", label: "Resolved" },
  rejected:    { icon: XCircle,      color: "text-rose-400",    bg: "bg-rose-400/10",    label: "Rejected" },
  wontfix:     { icon: XCircle,      color: "text-zinc-400",    bg: "bg-zinc-400/10",    label: "Won't Fix" },
} as const;

const ADMIN_ACTIONS: { status: string; label: string; hoverBg: string; hoverText: string }[] = [
  { status: "in_progress", label: "In Progress", hoverBg: "hover:bg-blue-400/20", hoverText: "hover:text-blue-400" },
  { status: "resolved",    label: "Resolve",     hoverBg: "hover:bg-emerald-400/20", hoverText: "hover:text-emerald-400" },
  { status: "rejected",    label: "Reject",      hoverBg: "hover:bg-rose-400/20", hoverText: "hover:text-rose-400" },
  { status: "wontfix",     label: "Won't Fix",   hoverBg: "hover:bg-zinc-400/20", hoverText: "hover:text-zinc-300" },
];

export default function IssueReports({ currentUser }: IssueReportsProps) {
  const { toast } = useToast();
  const [reports, setReports] = useState<IssueReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("bug");
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchAuthMe(currentUser)
      .then((me) => setIsAdmin(me.is_admin))
      .catch(() => setIsAdmin(false));
  }, [currentUser]);

  useEffect(() => {
    fetchReports()
      .then(setReports)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load reports."))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) return;
    setError(null);
    setSubmitting(true);
    try {
      const report = await createReport(
        { title: title.trim(), description: description.trim(), category, is_anonymous: isAnonymous },
        currentUser,
      );
      setReports((prev) => [report, ...prev]);
      setTitle("");
      setDescription("");
      setCategory("bug");
      setIsAnonymous(false);
      setShowForm(false);
      toast("Report submitted", "success");
    } catch (e: any) {
      const msg = e.response?.data?.detail || "Failed to submit report";
      setError(msg);
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteReport(id, currentUser);
      setReports((prev) => prev.filter((r) => r.id !== id));
      toast("Report deleted", "success");
    } catch (e: any) {
      toast(e.response?.data?.detail || "Failed to delete", "error");
    }
  };

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await updateReportStatus(id, status, currentUser);
      setReports((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: status as IssueReport["status"] } : r)),
      );
      toast(`Status updated to '${status}'`, "success");
    } catch (e: any) {
      toast(e.response?.data?.detail || "Failed to update status", "error");
    }
  };

  const openCount = reports.filter((r) => r.status === "open" || r.status === "in_progress").length;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">Issue Reports</h3>
          {openCount > 0 && (
            <span className="rounded-full bg-amber-400/20 px-2 py-0.5 text-xs font-medium text-amber-400">
              {openCount} open
            </span>
          )}
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          New Report
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-red-400">{error}</div>
      )}

      {/* New report form */}
      {showForm && (
        <div className="mb-4 rounded-lg border border-border bg-muted/20 p-4 space-y-3">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the issue..."
            rows={3}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
          />
          <div className="flex items-center gap-4">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="bug">Bug</option>
              <option value="feature">Feature Request</option>
              <option value="question">Question</option>
              <option value="other">Other</option>
            </select>
            <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isAnonymous}
                onChange={(e) => setIsAnonymous(e.target.checked)}
                className="rounded border-input"
              />
              <EyeOff className="h-3.5 w-3.5" />
              Anonymous
            </label>
            <div className="flex-1" />
            <button
              onClick={() => setShowForm(false)}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!title.trim() || !description.trim() || submitting}
              className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Submit
            </button>
          </div>
        </div>
      )}

      {/* Report list */}
      <div className="max-h-[32rem] overflow-y-auto rounded-lg border border-border bg-muted/20">
        {loading ? (
          <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading...
          </div>
        ) : reports.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            No reports yet. Click &ldquo;New Report&rdquo; to submit one.
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            {reports.map((report) => {
              const catCfg = CATEGORY_CONFIG[report.category] || CATEGORY_CONFIG.other;
              const stsCfg = STATUS_CONFIG[report.status] || STATUS_CONFIG.open;
              const CatIcon = catCfg.icon;
              const StsIcon = stsCfg.icon;
              const expanded = expandedId === report.id;

              return (
                <div key={report.id} className="hover:bg-muted/30">
                  {/* Summary row */}
                  <div
                    className="flex items-center justify-between px-4 py-2.5 cursor-pointer"
                    onClick={() => setExpandedId(expanded ? null : report.id)}
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <span className="font-medium text-sm truncate">{report.title}</span>
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${catCfg.bg} ${catCfg.color}`}>
                        <CatIcon className="h-3 w-3" />
                        {catCfg.label}
                      </span>
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${stsCfg.bg} ${stsCfg.color}`}>
                        <StsIcon className="h-3 w-3" />
                        {stsCfg.label}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        by {report.reported_by} &middot; {report.created_at.slice(0, 16)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 ml-2 shrink-0">
                      {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {expanded && (
                    <div className="px-4 pb-3 space-y-2">
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">{report.description}</p>
                      {report.admin_note && (
                        <p className="text-xs text-muted-foreground border-l-2 border-border pl-3">
                          Admin note: {report.admin_note}
                        </p>
                      )}
                      <div className="flex items-center gap-1 pt-1">
                        {/* Admin status actions */}
                        {isAdmin && report.status !== "resolved" && report.status !== "wontfix" && (
                          ADMIN_ACTIONS
                            .filter((a) => a.status !== report.status)
                            .map((a) => (
                              <button
                                key={a.status}
                                onClick={(e) => { e.stopPropagation(); handleStatusChange(report.id, a.status); }}
                                className={`rounded px-2 py-1 text-xs text-muted-foreground ${a.hoverBg} ${a.hoverText}`}
                                title={a.label}
                              >
                                {a.label}
                              </button>
                            ))
                        )}
                        {isAdmin && (report.status === "resolved" || report.status === "wontfix" || report.status === "rejected") && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusChange(report.id, "open"); }}
                            className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-amber-400/20 hover:text-amber-400"
                          >
                            Reopen
                          </button>
                        )}
                        {/* Delete: owner or admin */}
                        {(report.reported_by === currentUser || isAdmin) && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDelete(report.id); }}
                            className="rounded p-1 text-muted-foreground hover:bg-destructive/20 hover:text-red-400 ml-auto"
                            title="Delete report"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
