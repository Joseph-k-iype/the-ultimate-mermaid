import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, type PublishFromScanRequest } from "../api/client";

interface Props {
  scanId: string;
  perspectives: string[];
  activePerspective: string;
  onClose: () => void;
  components?: string[];
}

const PERSPECTIVE_LABELS: Record<string, string> = {
  manifest: "Data Manifest",
  er: "ER Diagram",
  dataflow: "Data Flow",
};

export default function PublishPatternModal({
  scanId,
  perspectives,
  activePerspective,
  onClose,
  components,
}: Props) {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [owner, setOwner] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(
    activePerspective === "all" 
      ? new Set(perspectives) 
      : new Set([activePerspective])
  );

  const mutation = useMutation({
    mutationFn: (req: PublishFromScanRequest) =>
      api.publishPatternFromScan(scanId, req),
    onSuccess: (data) => {
      navigate(`/patterns/${data.id}`);
    },
  });

  const togglePerspective = (p: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(p)) {
        next.delete(p);
      } else {
        next.add(p);
      }
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !owner.trim()) return;

    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    mutation.mutate({
      title: title.trim(),
      description: description.trim(),
      owner: owner.trim(),
      tags,
      perspectives: [...selected],
      ...(selectedComponent ? { component: selectedComponent } : {}),
    });
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
        <h2 className="text-lg font-semibold text-stone-900 mb-4">
          Publish as Pattern
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-stone-600 mb-1">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400"
              placeholder="My Architecture Pattern"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-600 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400"
              placeholder="Brief description of this pattern"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-stone-600 mb-1">
                Owner
              </label>
              <input
                type="text"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-600 mb-1">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400"
                placeholder="api, auth, microservice"
              />
            </div>
          </div>

          {components && components.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-stone-600 mb-1">
                Scope to Component (optional)
              </label>
              <select
                value={selectedComponent || ""}
                onChange={(e) => setSelectedComponent(e.target.value || null)}
                className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400 text-sm"
              >
                <option value="">All components (entire scan)</option>
                {components.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-stone-600 mb-2">
              Include Perspectives
            </label>
            <div className="flex flex-wrap gap-2">
              {perspectives.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => togglePerspective(p)}
                  className={`text-sm px-3 py-1.5 rounded-lg border ${
                    selected.has(p)
                      ? "bg-stone-900 text-white border-stone-900"
                      : "bg-white text-stone-500 border-stone-300 hover:border-stone-400"
                  }`}
                >
                  {PERSPECTIVE_LABELS[p] || p}
                </button>
              ))}
            </div>
            {selected.size === 0 && (
              <p className="text-amber-600 text-xs mt-1">
                Select at least one perspective
              </p>
            )}
          </div>

          {mutation.isError && (
            <p className="text-red-500 text-sm">{mutation.error.message}</p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-stone-600 hover:text-stone-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={
                mutation.isPending || selected.size === 0 || !title.trim() || !owner.trim()
              }
              className="bg-stone-900 text-white px-4 py-2 text-sm rounded-lg hover:bg-stone-800 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mutation.isPending ? "Publishing..." : "Publish"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
