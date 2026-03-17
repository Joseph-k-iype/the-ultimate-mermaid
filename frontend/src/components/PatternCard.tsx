import { Link } from "react-router-dom";
import type { PatternListItem } from "../api/client";
import StatusBadge from "./StatusBadge";

export default function PatternCard({ pattern }: { pattern: PatternListItem }) {
  return (
    <Link
      to={`/patterns/${pattern.id}`}
      className="block bg-white rounded-xl border border-stone-200 p-4 hover:border-stone-300 transition-colors"
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-sm font-semibold text-stone-900 truncate flex-1 mr-2">
          {pattern.title}
        </h3>
        <StatusBadge status={pattern.status} />
      </div>
      <p className="text-xs text-stone-400 mb-3 line-clamp-2">
        {pattern.description}
      </p>
      <div className="flex items-center justify-between text-xs text-stone-400">
        <span>{pattern.owner}</span>
        <span>v{pattern.version}</span>
      </div>
      {pattern.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
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
    </Link>
  );
}
