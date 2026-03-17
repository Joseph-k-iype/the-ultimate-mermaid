import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type PatternStatus } from "../api/client";
import MarkdownRenderer from "../components/MarkdownRenderer";
import StatusBadge from "../components/StatusBadge";

const TRANSITIONS: Record<PatternStatus, PatternStatus[]> = {
  draft: ["review"],
  review: ["approved", "draft"],
  approved: ["deprecated"],
  deprecated: ["draft"],
};

export default function PatternDetailPage() {
  const { patternId } = useParams<{ patternId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: pattern, isLoading } = useQuery({
    queryKey: ["pattern", patternId],
    queryFn: () => api.getPattern(patternId!),
    enabled: !!patternId,
  });

  const { data: relatedData } = useQuery({
    queryKey: ["related-patterns", patternId],
    queryFn: () => api.getRelatedPatterns(patternId!),
    enabled: !!patternId,
  });

  const transitionMutation = useMutation({
    mutationFn: (status: PatternStatus) =>
      api.transitionPattern(patternId!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pattern", patternId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deletePattern(patternId!),
    onSuccess: () => navigate("/patterns"),
  });

  if (isLoading) return <p className="text-stone-400 text-sm max-w-5xl mx-auto">Loading...</p>;
  if (!pattern) return <p className="text-red-500 text-sm max-w-5xl mx-auto">Pattern not found.</p>;

  const allowedTransitions = TRANSITIONS[pattern.status] || [];
  const related = relatedData?.results || [];

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <Link to="/patterns" className="text-sm text-stone-500 hover:text-stone-900">
          &larr; Back to Library
        </Link>
      </div>

      <div className="bg-white rounded-xl border border-stone-200 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold text-stone-900 tracking-tight mb-1">
              {pattern.title}
            </h1>
            <div className="flex items-center gap-3 text-sm text-stone-400">
              <StatusBadge status={pattern.status} />
              <span>by {pattern.owner}</span>
              <span>v{pattern.version}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Link
              to={`/patterns/${pattern.id}/edit`}
              className="bg-stone-100 text-stone-700 px-3 py-1.5 rounded-lg text-sm hover:bg-stone-200"
            >
              Edit
            </Link>
            <button
              onClick={() => {
                if (confirm("Delete this pattern?")) {
                  deleteMutation.mutate();
                }
              }}
              className="text-red-600 border border-red-200 hover:bg-red-50 rounded-lg px-3 py-1.5 text-sm"
            >
              Delete
            </button>
          </div>
        </div>

        {pattern.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {pattern.tags.map((tag) => (
              <span
                key={tag}
                className="bg-stone-100 text-stone-600 rounded-md px-2 py-0.5 text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {allowedTransitions.length > 0 && (
          <div className="flex gap-2 mb-6 pb-4 border-b border-stone-100">
            <span className="text-xs text-stone-400 self-center mr-1">
              Transition to:
            </span>
            {allowedTransitions.map((s) => (
              <button
                key={s}
                onClick={() => transitionMutation.mutate(s)}
                disabled={transitionMutation.isPending}
                className="bg-stone-100 text-stone-700 px-3 py-1 rounded-lg text-xs hover:bg-stone-200 disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {pattern.linked_scan_id && (
          <p className="text-xs text-stone-400 mb-4">
            Linked scan:{" "}
            <Link
              to={`/scan/${pattern.linked_scan_id}`}
              className="text-stone-600 hover:text-stone-900"
            >
              {pattern.linked_scan_id.slice(0, 12)}...
            </Link>
          </p>
        )}

        <MarkdownRenderer content={pattern.content} />
      </div>

      {related.length > 0 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-stone-900 tracking-tight mb-3">
            Related Patterns
          </h2>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {related.map((r) => (
              <Link
                key={r.id}
                to={`/patterns/${r.id}`}
                className="flex-shrink-0 bg-white border border-stone-200 rounded-xl p-4 w-56 hover:border-stone-300"
              >
                <p className="text-sm font-medium text-stone-900 truncate">
                  {r.title}
                </p>
                <p className="text-xs text-stone-400 truncate mt-1">
                  {r.description}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
