import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type TemplateResponse } from "../api/client";
import TemplateEditor from "../components/TemplateEditor";
import PlaceholderForm from "../components/PlaceholderForm";

export default function TemplatePage() {
  const [selected, setSelected] = useState<TemplateResponse | null>(null);
  const queryClient = useQueryClient();

  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: api.listTemplates,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      setSelected(null);
    },
  });

  return (
    <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="space-y-6">
        <div className="bg-white border border-stone-200 rounded-xl p-6">
          <TemplateEditor />
        </div>

        {templates && templates.length > 0 && (
          <div className="bg-white border border-stone-200 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-stone-900 tracking-tight mb-3">Saved Templates</h3>
            <ul className="divide-y divide-stone-100">
              {templates.map((t) => (
                <li
                  key={t.id}
                  className="py-2 flex justify-between items-center"
                >
                  <button
                    onClick={() => setSelected(t)}
                    className="text-sm text-stone-700 hover:text-stone-900"
                  >
                    {t.name}
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(t.id)}
                    className="text-xs text-red-600 border border-red-200 hover:bg-red-50 rounded-lg px-2 py-0.5"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div>
        {selected ? (
          <div className="bg-white border border-stone-200 rounded-xl p-6">
            <PlaceholderForm template={selected} />
          </div>
        ) : (
          <div className="bg-white border border-stone-200 rounded-xl p-6 text-stone-400 text-center">
            Select a template to render
          </div>
        )}
      </div>
    </div>
  );
}
