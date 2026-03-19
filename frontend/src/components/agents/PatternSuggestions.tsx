import type { DetectedPattern } from "../../types/agents";

interface PatternSuggestionsProps {
  patterns: DetectedPattern[];
}

export default function PatternSuggestions({ patterns }: PatternSuggestionsProps) {
  if (patterns.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-stone-700">Detected Patterns</h3>
      {patterns.map((pattern, i) => (
        <div
          key={i}
          className="bg-white border border-stone-200 rounded-lg p-3 shadow-sm"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-stone-800">
              {pattern.pattern_type}
            </span>
            <div className="flex items-center gap-1">
              <div className="w-12 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-stone-500 rounded-full"
                  style={{ width: `${pattern.confidence * 100}%` }}
                />
              </div>
              <span className="text-xs text-stone-400">
                {Math.round(pattern.confidence * 100)}%
              </span>
            </div>
          </div>
          <p className="text-xs text-stone-600">{pattern.description}</p>
          {pattern.entities_involved.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {pattern.entities_involved.slice(0, 5).map((entity, j) => (
                <span
                  key={j}
                  className="text-xs px-1.5 py-0.5 bg-stone-100 text-stone-500 rounded"
                >
                  {entity}
                </span>
              ))}
              {pattern.entities_involved.length > 5 && (
                <span className="text-xs text-stone-400">
                  +{pattern.entities_involved.length - 5} more
                </span>
              )}
            </div>
          )}
          {pattern.related_perspectives.length > 0 && (
            <div className="mt-1 flex gap-1">
              {pattern.related_perspectives.map((p, j) => (
                <span
                  key={j}
                  className="text-xs px-1.5 py-0.5 bg-stone-50 text-stone-400 rounded border border-stone-100"
                >
                  {p}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
