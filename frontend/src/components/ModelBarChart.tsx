import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { type WorkspaceRanking } from "@/lib/api";

interface ModelBarChartProps {
  data: WorkspaceRanking[];
}

export default function ModelBarChart({ data }: ModelBarChartProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h3 className="mb-4 text-lg font-semibold">Chats by Workspace</h3>
      {data.length === 0 ? (
        <p className="py-10 text-center text-muted-foreground">No data</p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 40 + 40)}>
          <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis type="number" stroke="hsl(var(--muted-foreground))" />
            <YAxis
              dataKey="name"
              type="category"
              width={160}
              tick={{ fontSize: 12 }}
              stroke="hsl(var(--muted-foreground))"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
              }}
            />
            <Bar dataKey="chat_count" name="Chats" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
