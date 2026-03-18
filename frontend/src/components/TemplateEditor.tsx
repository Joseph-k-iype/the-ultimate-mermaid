import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

const PERSPECTIVES = ["er", "dataflow", "manifest"];

export default function TemplateEditor() {
  const [name, setName] = useState("");
  const [perspective, setPerspective] = useState("er");
  const [content, setContent] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => {
      const placeholders = [...content.matchAll(/\{\{\s*(\w+)\s*\}\}/g)].map(
        (m) => m[1]
      );
      return api.createTemplate({
        name,
        perspective,
        template_content: content,
        placeholders: [...new Set(placeholders)],
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      setName("");
      setContent("");
    },
  });

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-stone-900 tracking-tight">Create Template</h3>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Template name"
        className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-stone-400 focus:outline-none"
      />
      <select
        value={perspective}
        onChange={(e) => setPerspective(e.target.value)}
        className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-stone-400 focus:outline-none"
      >
        {PERSPECTIVES.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Mermaid template with {{ placeholders }}"
        rows={10}
        className="w-full px-3 py-2 border border-stone-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
      />
      <button
        onClick={() => mutation.mutate()}
        disabled={!name || !content || mutation.isPending}
        className="bg-stone-900 text-white py-2 px-4 rounded-lg hover:bg-stone-800 disabled:opacity-50"
      >
        Save Template
      </button>
      {mutation.isError && (
        <p className="text-red-500 text-sm">{mutation.error.message}</p>
      )}
    </div>
  );
}
