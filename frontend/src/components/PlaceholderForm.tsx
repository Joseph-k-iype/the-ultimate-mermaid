import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type TemplateResponse } from "../api/client";
import MermaidRenderer from "./MermaidRenderer";

export default function PlaceholderForm({
  template,
}: {
  template: TemplateResponse;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(template.placeholders.map((p) => [p, ""]))
  );
  const [rendered, setRendered] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.renderTemplate(template.id, values),
    onSuccess: (data) => setRendered(data.rendered),
  });

  return (
    <div className="space-y-3">
      <h4 className="font-semibold text-stone-900 tracking-tight">{template.name}</h4>
      {template.placeholders.map((ph) => (
        <div key={ph}>
          <label className="block text-sm text-stone-600 mb-1">{ph}</label>
          <input
            type="text"
            value={values[ph] || ""}
            onChange={(e) =>
              setValues((prev) => ({ ...prev, [ph]: e.target.value }))
            }
            className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
          />
        </div>
      ))}
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="bg-stone-900 text-white py-2 px-4 rounded-lg hover:bg-stone-800 disabled:opacity-50 text-sm"
      >
        Render
      </button>
      {mutation.isError && (
        <p className="text-red-500 text-sm">{mutation.error.message}</p>
      )}
      {rendered && (
        <div className="mt-4 border border-stone-200 rounded-xl p-4">
          <MermaidRenderer code={rendered} />
        </div>
      )}
    </div>
  );
}
