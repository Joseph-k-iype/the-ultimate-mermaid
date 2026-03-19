import { useState } from "react";
import type { AgentInsight } from "../../types/agents";

const severityStyles = {
  info: "bg-stone-100 text-stone-600",
  warning: "bg-amber-50 text-amber-700",
  critical: "bg-red-50 text-red-700",
};

const severityDot = {
  info: "bg-stone-400",
  warning: "bg-amber-500",
  critical: "bg-red-500",
};

interface InsightCardProps {
  insight: AgentInsight;
  defaultExpanded?: boolean;
}

export default function InsightCard({ insight, defaultExpanded = false }: InsightCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className={`rounded-xl border border-stone-200/60 p-3.5 transition-all duration-200 hover:shadow-sm ${severityStyles[insight.severity]}`}>
      <div
        className="flex items-start gap-2 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${severityDot[insight.severity]}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-sm font-medium truncate">{insight.title}</h4>
            <div className="flex items-center gap-2 flex-shrink-0">
              <div className="w-16 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-stone-500 rounded-full"
                  style={{ width: `${insight.confidence * 100}%` }}
                />
              </div>
              <span className="text-xs text-stone-400">{Math.round(insight.confidence * 100)}%</span>
            </div>
          </div>
          <p className="text-xs mt-0.5 line-clamp-2">{insight.description}</p>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 ml-4 space-y-2">
          {insight.evidence.length > 0 && (
            <div>
              <p className="text-xs font-medium text-stone-500 mb-1">Evidence</p>
              <ul className="text-xs space-y-0.5">
                {insight.evidence.map((e, i) => (
                  <li key={i} className="text-stone-600">{"\u2022"} {e}</li>
                ))}
              </ul>
            </div>
          )}
          {insight.recommendations.length > 0 && (
            <div>
              <p className="text-xs font-medium text-stone-500 mb-1">Recommendations</p>
              <ul className="text-xs space-y-0.5">
                {insight.recommendations.map((r, i) => (
                  <li key={i} className="text-stone-600">{"\u2022"} {r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
