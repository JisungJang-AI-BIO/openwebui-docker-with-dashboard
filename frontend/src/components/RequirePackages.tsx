import { useState, useEffect } from "react";
import { Download, X, Info, Plus, Check, Ban, Clock, Loader2, Undo2, ExternalLink } from "lucide-react";
import { fetchPackages, addPackage, deletePackage, updatePackageStatus, type PythonPackage } from "@/lib/api";

interface RequirePackagesProps {
  currentUser: string;
}

const STATUS_CONFIG = {
  pending:     { icon: Clock,  color: "text-amber-400",   bg: "bg-amber-400/10",   label: "Pending" },
  installed:   { icon: Check,  color: "text-emerald-400", bg: "bg-emerald-400/10", label: "Installed" },
  rejected:    { icon: Ban,    color: "text-rose-400",    bg: "bg-rose-400/10",    label: "Rejected" },
  uninstalled: { icon: Undo2,  color: "text-zinc-400",    bg: "bg-zinc-400/10",    label: "Uninstalled" },
} as const;

// Hardcoded for now; in production this comes from /api/auth/me
const ADMIN_USERS = ["jisung.jang"];

export default function RequirePackages({ currentUser }: RequirePackagesProps) {
  const [packages, setPackages] = useState<PythonPackage[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTooltip, setShowTooltip] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const isAdmin = ADMIN_USERS.includes(currentUser);

  useEffect(() => {
    fetchPackages()
      .then(setPackages)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleAdd = async () => {
    const name = input.trim().toLowerCase();
    if (!name || !currentUser) return;
    setError(null);
    setSubmitting(true);
    try {
      const pkg = await addPackage(name, currentUser);
      setPackages((prev) => [pkg, ...prev]);
      setInput("");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to add package");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      await deletePackage(id, currentUser);
      setPackages((prev) => prev.filter((p) => p.id !== id));
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to delete package");
    }
  };

  const handleStatusChange = async (id: number, status: string) => {
    setError(null);
    try {
      await updatePackageStatus(id, status, currentUser);
      setPackages((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: status as PythonPackage["status"] } : p))
      );
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to update status");
    }
  };

  const handleExport = () => {
    const content = [...packages]
      .reverse()
      .map((p) => p.package_name)
      .join("\n");
    const blob = new Blob([content + "\n"], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "requirements.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  const pendingCount = packages.filter((p) => p.status === "pending").length;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">Require Python Packages</h3>
          {pendingCount > 0 && (
            <span className="rounded-full bg-amber-400/20 px-2 py-0.5 text-xs font-medium text-amber-400">
              {pendingCount} pending
            </span>
          )}
          <div className="relative">
            <button type="button" onClick={() => setShowTooltip((v) => !v)}>
              <Info className="h-4 w-4 text-muted-foreground hover:text-foreground" />
            </button>
            {showTooltip && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowTooltip(false)} />
                <div className="absolute left-6 top-0 z-20 w-80 rounded-lg border border-border bg-popover p-3 text-sm text-popover-foreground shadow-lg">
                  <p>Request Python packages to use 'python packages' for your workspace on SbioChat.</p>
                  <a
                    href="https://docs.openwebui.com/features/plugin/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Ref: Open WebUI Plugin Docs
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </>
            )}
          </div>
        </div>
        <button
          onClick={handleExport}
          disabled={packages.length === 0}
          className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Download className="h-4 w-4" />
          Export
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Package list */}
      <div className="mb-4 max-h-80 overflow-y-auto rounded-lg border border-border bg-muted/20">
        {loading ? (
          <div className="flex items-center justify-center gap-2 p-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading...
          </div>
        ) : packages.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            No packages requested yet. Add one below.
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            {packages.map((pkg) => {
              const cfg = STATUS_CONFIG[pkg.status] || STATUS_CONFIG.pending;
              const StatusIcon = cfg.icon;
              return (
                <div
                  key={pkg.id}
                  className="flex items-center justify-between px-4 py-2.5 hover:bg-muted/30"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <span className="font-mono text-sm font-medium">{pkg.package_name}</span>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${cfg.bg} ${cfg.color}`}>
                      <StatusIcon className="h-3 w-3" />
                      {cfg.label}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      by {pkg.added_by} &middot; {pkg.added_at.slice(0, 16)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 ml-2 shrink-0">
                    {/* Admin actions */}
                    {isAdmin && pkg.status === "pending" && (
                      <>
                        <button
                          onClick={() => handleStatusChange(pkg.id, "installed")}
                          className="rounded p-1 text-muted-foreground hover:bg-emerald-400/20 hover:text-emerald-400"
                          title="Mark as installed"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleStatusChange(pkg.id, "rejected")}
                          className="rounded p-1 text-muted-foreground hover:bg-rose-400/20 hover:text-rose-400"
                          title="Reject"
                        >
                          <Ban className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                    {isAdmin && pkg.status === "installed" && (
                      <button
                        onClick={() => handleStatusChange(pkg.id, "uninstalled")}
                        className="rounded p-1 text-muted-foreground hover:bg-zinc-400/20 hover:text-zinc-300"
                        title="Mark as uninstalled"
                      >
                        <Undo2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                    {isAdmin && (pkg.status === "rejected" || pkg.status === "uninstalled") && (
                      <button
                        onClick={() => handleStatusChange(pkg.id, "pending")}
                        className="rounded p-1 text-muted-foreground hover:bg-amber-400/20 hover:text-amber-400"
                        title="Revert to pending"
                      >
                        <Clock className="h-3.5 w-3.5" />
                      </button>
                    )}
                    {/* Delete: owner or admin */}
                    {(pkg.added_by === currentUser || isAdmin) && (
                      <button
                        onClick={() => handleDelete(pkg.id)}
                        className="rounded p-1 text-muted-foreground hover:bg-destructive/20 hover:text-red-400"
                        title="Remove request"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="package-name (e.g. numpy, pandas, transformers)"
          className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          disabled={!currentUser || submitting}
        />
        <button
          onClick={handleAdd}
          disabled={!input.trim() || !currentUser || submitting}
          className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Request
        </button>
      </div>
    </div>
  );
}
