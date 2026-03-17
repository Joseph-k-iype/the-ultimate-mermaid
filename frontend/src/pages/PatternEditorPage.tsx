import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import MarkdownRenderer from "../components/MarkdownRenderer";

export default function PatternEditorPage() {
  const { patternId } = useParams<{ patternId: string }>();
  const navigate = useNavigate();
  const isEdit = !!patternId;

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [owner, setOwner] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [content, setContent] = useState("");
  const [initialized, setInitialized] = useState(false);

  // Load existing pattern for edit mode
  const { data: existing } = useQuery({
    queryKey: ["pattern", patternId],
    queryFn: () => api.getPattern(patternId!),
    enabled: isEdit,
  });

  // Load template for new mode
  const { data: templateData } = useQuery({
    queryKey: ["pattern-template"],
    queryFn: () => api.getPatternTemplate(),
    enabled: !isEdit,
  });

  useEffect(() => {
    if (initialized) return;
    if (isEdit && existing) {
      setTitle(existing.title);
      setDescription(existing.description);
      setOwner(existing.owner);
      setTagsInput(existing.tags.join(", "));
      setContent(existing.content);
      setInitialized(true);
    } else if (!isEdit && templateData) {
      setContent(templateData.content);
      setInitialized(true);
    }
  }, [existing, templateData, isEdit, initialized]);

  const createMutation = useMutation({
    mutationFn: () =>
      api.createPattern({
        title,
        description,
        owner,
        tags: tagsInput.split(",").map((t) => t.trim()).filter(Boolean),
        content,
      }),
    onSuccess: (data) => navigate(`/patterns/${data.id}`),
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      api.updatePattern(patternId!, {
        title,
        description,
        owner,
        tags: tagsInput.split(",").map((t) => t.trim()).filter(Boolean),
        content,
      }),
    onSuccess: () => navigate(`/patterns/${patternId}`),
  });

  const handleSave = () => {
    if (isEdit) {
      updateMutation.mutate();
    } else {
      createMutation.mutate();
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  return (
    <div className="max-w-7xl mx-auto">
      <h1 className="text-xl font-semibold text-stone-900 tracking-tight mb-6">
        {isEdit ? "Edit Pattern" : "New Pattern"}
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
        <input
          type="text"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="border border-stone-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
        />
        <input
          type="text"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="border border-stone-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
        />
        <input
          type="text"
          placeholder="Owner"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          className="border border-stone-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
        />
        <input
          type="text"
          placeholder="Tags (comma-separated)"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          className="border border-stone-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-stone-400 mb-1">
            Content (Markdown + Mermaid)
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-[600px] border border-stone-300 rounded-lg px-3 py-2 text-sm font-mono resize-none focus:ring-2 focus:ring-stone-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-stone-400 mb-1">
            Preview
          </label>
          <div className="border border-stone-200 rounded-lg p-4 h-[600px] overflow-auto bg-white">
            <MarkdownRenderer content={content} />
          </div>
        </div>
      </div>

      {error && (
        <p className="text-red-500 text-sm mt-2">{(error as Error).message}</p>
      )}

      <div className="flex gap-2 mt-4">
        <button
          onClick={handleSave}
          disabled={isPending || !title || !owner}
          className="bg-stone-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-stone-800 disabled:opacity-50"
        >
          {isPending ? "Saving..." : "Save"}
        </button>
        <button
          onClick={() => navigate(isEdit ? `/patterns/${patternId}` : "/patterns")}
          className="bg-stone-100 text-stone-700 px-4 py-2 rounded-lg text-sm hover:bg-stone-200"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
