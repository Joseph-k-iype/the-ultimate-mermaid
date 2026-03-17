import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type PatternStatus } from "../api/client";
import PatternCard from "../components/PatternCard";

export default function PatternLibraryPage() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<PatternStatus | "">("");
  const [owner, setOwner] = useState("");
  const [tagsInput, setTagsInput] = useState("");

  const tags = tagsInput
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const { data, isLoading } = useQuery({
    queryKey: ["patterns", query, status, owner, tagsInput],
    queryFn: () =>
      api.searchPatterns({
        query: query || undefined,
        status: (status as PatternStatus) || undefined,
        owner: owner || undefined,
        tags: tags.length ? tags : undefined,
      }),
  });

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-stone-900 tracking-tight">Pattern Library</h1>
        <Link
          to="/patterns/new"
          className="bg-stone-900 text-white px-4 py-2 rounded-lg text-sm hover:bg-stone-800"
        >
          New Pattern
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <input
          type="text"
          placeholder="Search patterns..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="border border-stone-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
        />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as PatternStatus | "")}
          className="border border-stone-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-stone-400 focus:outline-none"
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="review">Review</option>
          <option value="approved">Approved</option>
          <option value="deprecated">Deprecated</option>
        </select>
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

      {isLoading && <p className="text-stone-400 text-sm">Loading...</p>}

      {data && data.total === 0 && (
        <p className="text-stone-400 text-sm">
          No patterns found. Create one to get started.
        </p>
      )}

      {data && data.total > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.results.map((p) => (
            <PatternCard key={p.id} pattern={p} />
          ))}
        </div>
      )}
    </div>
  );
}
