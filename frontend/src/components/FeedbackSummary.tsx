import { type FeedbackSummary as FeedbackSummaryType } from "@/lib/api";

interface FeedbackSummaryProps {
  data: FeedbackSummaryType | null;
}

export default function FeedbackSummary({ data }: FeedbackSummaryProps) {
  if (!data) return null;

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h3 className="mb-4 text-lg font-semibold">Feedback</h3>
      <div className="mb-6 flex gap-6">
        <div className="flex items-center gap-2">
          <span className="text-xl">{"\ud83d\udc4d"}</span>
          <span className="text-2xl font-bold">{data.positive}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xl">{"\ud83d\udc4e"}</span>
          <span className="text-2xl font-bold">{data.negative}</span>
        </div>
      </div>
      {data.recent.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-medium text-muted-foreground">Recent Feedback</h4>
          <div className="space-y-2">
            {data.recent.map((fb) => (
              <div key={fb.id} className="flex items-start gap-3 rounded-lg bg-muted/50 p-3">
                <span className="mt-0.5 text-base">{fb.rating > 0 ? "\ud83d\udc4d" : "\ud83d\udc4e"}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">{fb.model_id}</span>
                    <span className="text-xs text-muted-foreground">{fb.created_at.slice(0, 16)}</span>
                  </div>
                  {fb.comment && <p className="mt-1 text-sm">{fb.comment}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
