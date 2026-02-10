import { useState } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { type WorkspaceRanking } from "@/lib/api";

interface WorkspaceRankingTableProps {
  data: WorkspaceRanking[];
}

type SortKey = "user_count" | "chat_count" | "message_count" | "positive" | "negative";
type SortDir = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "user_count", label: "Users" },
  { key: "chat_count", label: "Chats" },
  { key: "message_count", label: "Messages" },
  { key: "positive", label: "\ud83d\udc4d" },
  { key: "negative", label: "\ud83d\udc4e" },
];

export default function WorkspaceRankingTable({ data }: WorkspaceRankingTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("chat_count");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "desc" ? "asc" : "desc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...data].sort((a, b) => {
    const diff = a[sortKey] - b[sortKey];
    return sortDir === "desc" ? -diff : diff;
  });

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ArrowUpDown className="ml-1 inline h-3.5 w-3.5 opacity-40" />;
    return sortDir === "desc"
      ? <ArrowDown className="ml-1 inline h-3.5 w-3.5" />
      : <ArrowUp className="ml-1 inline h-3.5 w-3.5" />;
  };

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h3 className="mb-4 text-lg font-semibold">Workspace Ranking</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="pb-3 pr-4 font-medium w-12">#</th>
              <th className="pb-3 pr-4 font-medium">Workspace</th>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className="pb-3 pr-4 font-medium text-right cursor-pointer select-none hover:text-foreground"
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  <SortIcon col={col.key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((ws, i) => (
              <tr key={ws.id} className="border-b border-border/50 hover:bg-muted/50">
                <td className="py-3 pr-4 text-muted-foreground font-mono">{i + 1}</td>
                <td className="py-3 pr-4">
                  <div>
                    <span className="font-medium">{ws.name}</span>
                    {ws.name !== ws.id && (
                      <span className="ml-2 text-xs text-muted-foreground">{ws.id}</span>
                    )}
                  </div>
                </td>
                <td className="py-3 pr-4 text-right font-mono">{ws.user_count}</td>
                <td className="py-3 pr-4 text-right font-mono">{ws.chat_count}</td>
                <td className="py-3 pr-4 text-right font-mono">{ws.message_count}</td>
                <td className="py-3 pr-4 text-right">
                  <span className="font-mono text-emerald-400">{ws.positive}</span>
                </td>
                <td className="py-3 pr-4 text-right">
                  <span className="font-mono text-rose-400">{ws.negative}</span>
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="py-10 text-center text-muted-foreground">No workspace data.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
