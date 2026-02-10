import { useState } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { type GroupRanking } from "@/lib/api";

interface GroupRankingTableProps {
  data: GroupRanking[];
}

type SortKey = "member_count" | "total_chats" | "total_messages" | "rating" | "chats_per_member" | "messages_per_member";
type SortDir = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "member_count", label: "Members" },
  { key: "chats_per_member", label: "Chats/Member" },
  { key: "messages_per_member", label: "Msgs/Member" },
  { key: "total_chats", label: "Total Chats" },
  { key: "total_messages", label: "Total Msgs" },
  { key: "rating", label: "Rating" },
];

function getRating(row: GroupRanking) {
  return row.total_positive - row.total_negative;
}

function RatingCell({ value }: { value: number }) {
  if (value > 0) return <span className="font-mono text-emerald-400">+{value}</span>;
  if (value < 0) return <span className="font-mono text-rose-400">{value}</span>;
  return <span className="font-mono text-muted-foreground">0</span>;
}

export default function GroupRankingTable({ data }: GroupRankingTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("chats_per_member");
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
    const va = sortKey === "rating" ? getRating(a) : a[sortKey];
    const vb = sortKey === "rating" ? getRating(b) : b[sortKey];
    return sortDir === "desc" ? vb - va : va - vb;
  });

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ArrowUpDown className="ml-1 inline h-3.5 w-3.5 opacity-40" />;
    return sortDir === "desc"
      ? <ArrowDown className="ml-1 inline h-3.5 w-3.5" />
      : <ArrowUp className="ml-1 inline h-3.5 w-3.5" />;
  };

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h3 className="mb-4 text-lg font-semibold">Best Group Ranking</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="pb-3 pr-4 font-medium w-12">#</th>
              <th className="pb-3 pr-4 font-medium">Group</th>
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
            {sorted.map((g, i) => (
              <tr key={g.group_id} className="border-b border-border/50 hover:bg-muted/50">
                <td className="py-3 pr-4 text-muted-foreground font-mono">{i + 1}</td>
                <td className="py-3 pr-4 font-medium">{g.group_name}</td>
                <td className="py-3 pr-4 text-right font-mono">{g.member_count}</td>
                <td className="py-3 pr-4 text-right font-mono">{g.chats_per_member}</td>
                <td className="py-3 pr-4 text-right font-mono">{g.messages_per_member}</td>
                <td className="py-3 pr-4 text-right font-mono">{g.total_chats}</td>
                <td className="py-3 pr-4 text-right font-mono">{g.total_messages}</td>
                <td className="py-3 pr-4 text-right"><RatingCell value={getRating(g)} /></td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={8} className="py-10 text-center text-muted-foreground">No group data.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
