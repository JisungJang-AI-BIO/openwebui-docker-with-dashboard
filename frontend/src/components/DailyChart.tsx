import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { type DailyStat } from "@/lib/api";

interface DailyChartProps {
  data: DailyStat[];
  dateFrom: string;
  dateTo: string;
  onDateChange: (from: string, to: string) => void;
}

export default function DailyChart({ data, dateFrom, dateTo, onDateChange }: DailyChartProps) {
  const [from, setFrom] = useState(dateFrom);
  const [to, setTo] = useState(dateTo);

  const handleApply = () => onDateChange(from, to);

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <h3 className="text-lg font-semibold">Daily Usage</h3>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
          <span className="text-muted-foreground">~</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
          <button
            onClick={handleApply}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            Search
          </button>
        </div>
      </div>
      {data.length === 0 ? (
        <p className="py-10 text-center text-muted-foreground">No data for this period.</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
            <YAxis stroke="hsl(var(--muted-foreground))" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
              }}
            />
            <Legend />
            <Bar dataKey="user_count" name="Users" fill="#10b981" radius={[4, 4, 0, 0]} />
            <Bar dataKey="chat_count" name="Chats" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            <Bar dataKey="message_count" name="Messages" fill="#f59e0b" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
