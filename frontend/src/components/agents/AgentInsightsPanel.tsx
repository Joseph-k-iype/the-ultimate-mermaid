import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { AgentCategory, AgentInsight } from "../../types/agents";
import InsightCard from "./InsightCard";
import PatternDiagrams from "./PatternDiagrams";
import PatternSuggestions from "./PatternSuggestions";

const CATEGORIES: { key: AgentCategory; label: string }[] = [
  { key: "architecture", label: "Architecture" },
  { key: "code_quality", label: "Code Quality" },
  { key: "data_flow", label: "Data Flow" },
  { key: "service_flow", label: "Service Flow" },
  { key: "security", label: "Security" },
  { key: "performance", label: "Performance" },
  { key: "sdlc", label: "SDLC" },
];

interface AgentInsightsPanelProps {
  scanId: string;
  scanStatus: string;
}

export default function AgentInsightsPanel({ scanId, scanStatus }: AgentInsightsPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<AgentCategory | "all">("all");
  const queryClient = useQueryClient();

  const { data: result, isLoading } = useQuery({
    queryKey: ["agent-insights", scanId],
    queryFn: () => api.getAgentInsights(scanId),
    enabled: isOpen && scanStatus === "completed",
    retry: false,
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.triggerAgentAnalysis(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-insights", scanId] });
    },
  });

  const filteredInsights: AgentInsight[] =
    result?.insights?.filter(
      (i) => activeCategory === "all" || i.category === activeCategory
    ) ?? [];

  const statusBadge = result?.status ? (
    <span
      className={`text-xs px-1.5 py-0.5 rounded ${
        result.status === "success"
          ? "bg-emerald-100 text-emerald-700"
          : result.status === "partial"
          ? "bg-amber-100 text-amber-700"
          : "bg-red-100 text-red-700"
      }`}
    >
      {result.status}
    </span>
  ) : null;

  return (
    <div className="bg-white">
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3.5 flex items-center justify-between text-[13px] font-semibold text-stone-800 hover:bg-stone-50 transition-colors duration-200"
      >
        <span>AI Insights</span>
        <span className="text-stone-400">{isOpen ? "\u2212" : "+"}</span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            {statusBadge}
            {!result && scanStatus === "completed" && (
              <button
                onClick={() => analyzeMutation.mutate()}
                disabled={analyzeMutation.isPending}
                className="text-xs px-2 py-1 bg-stone-900 text-white rounded hover:bg-stone-800 disabled:opacity-50"
              >
                {analyzeMutation.isPending ? "Analyzing..." : "Analyze with AI"}
              </button>
            )}
          </div>

          {isLoading && <p className="text-xs text-stone-400">Loading insights...</p>}

          {analyzeMutation.isError && (
            <p className="text-xs text-red-500">
              Analysis failed: {(analyzeMutation.error as Error).message}
            </p>
          )}

          {result && (
            <>
              {/* Category tabs */}
              <div className="flex flex-wrap gap-1">
                <button
                  onClick={() => setActiveCategory("all")}
                  className={`text-xs px-2 py-1 rounded-full ${
                    activeCategory === "all"
                      ? "bg-stone-900 text-white"
                      : "bg-stone-200 text-stone-600 hover:bg-stone-300"
                  }`}
                >
                  All ({result.insights?.length ?? 0})
                </button>
                {CATEGORIES.map((cat) => {
                  const count = result.insights?.filter((i) => i.category === cat.key).length ?? 0;
                  if (count === 0) return null;
                  return (
                    <button
                      key={cat.key}
                      onClick={() => setActiveCategory(cat.key)}
                      className={`text-xs px-2 py-1 rounded-full ${
                        activeCategory === cat.key
                          ? "bg-stone-900 text-white"
                          : "bg-stone-200 text-stone-600 hover:bg-stone-300"
                      }`}
                    >
                      {cat.label} ({count})
                    </button>
                  );
                })}
              </div>

              {/* Insights */}
              <div className="space-y-2 max-h-[50vh] overflow-y-auto">
                {filteredInsights.map((insight, i) => (
                  <InsightCard key={i} insight={insight} />
                ))}
                {filteredInsights.length === 0 && (
                  <p className="text-xs text-stone-400 py-2">No insights in this category.</p>
                )}
              </div>

              {/* Pattern Diagrams */}
              {result.patterns && result.patterns.length > 0 && (
                <PatternDiagrams patterns={result.patterns} />
              )}

              {/* Patterns */}
              {result.patterns && result.patterns.length > 0 && (
                <PatternSuggestions patterns={result.patterns} />
              )}

              {/* Errors */}
              {result.errors && result.errors.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-red-500 mb-1">Errors</p>
                  {result.errors.map((err, i) => (
                    <p key={i} className="text-xs text-red-400">{err}</p>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
