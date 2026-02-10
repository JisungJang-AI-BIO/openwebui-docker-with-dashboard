import { ThumbsUp, ThumbsDown } from "lucide-react";
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
          <ThumbsUp className="h-5 w-5 text-emerald-400" />
          <span className="text-2xl font-bold">{data.positive}</span>
          <span className="text-sm text-muted-foreground">Positive</span>
        </div>
        <div className="flex items-center gap-2">
          <ThumbsDown className="h-5 w-5 text-rose-400" />
          <span className="text-2xl font-bold">{data.negative}</span>
          <span className="text-sm text-muted-foreground">Negative</span>
        </div>
      </div>
      {data.recent.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-medium text-muted-foreground">Recent Feedback</h4>
          <div className="space-y-2">
            {data.recent.map((fb) => (
              <div key={fb.id} className="flex items-start gap-3 rounded-lg bg-muted/50 p-3">
                {fb.rating > 0 ? (
                  <ThumbsUp className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                ) : (
                  <ThumbsDown className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                )}
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
