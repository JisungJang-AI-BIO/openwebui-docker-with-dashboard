import { type RecentChat } from "@/lib/api";

interface RecentChatsProps {
  data: RecentChat[];
}

export default function RecentChats({ data }: RecentChatsProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h3 className="mb-4 text-lg font-semibold">Recent Chats</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="pb-3 pr-4 font-medium">Title</th>
              <th className="pb-3 pr-4 font-medium">Model</th>
              <th className="pb-3 pr-4 font-medium text-center">Messages</th>
              <th className="pb-3 pr-4 font-medium">Created</th>
              <th className="pb-3 font-medium">Updated</th>
            </tr>
          </thead>
          <tbody>
            {data.map((chat) => (
              <tr key={chat.id} className="border-b border-border/50 hover:bg-muted/50">
                <td className="py-3 pr-4 font-medium">{chat.title}</td>
                <td className="py-3 pr-4">
                  <div className="flex flex-wrap gap-1">
                    {(chat.models || []).map((m) => (
                      <span key={m} className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                        {m}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-3 pr-4 text-center">{chat.message_count}</td>
                <td className="py-3 pr-4 text-muted-foreground">{chat.created_at.slice(0, 16)}</td>
                <td className="py-3 text-muted-foreground">{chat.updated_at.slice(0, 16)}</td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={5} className="py-10 text-center text-muted-foreground">No chat history.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
