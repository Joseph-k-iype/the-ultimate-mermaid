import type { PatternStatus } from "../api/client";

const STATUS_STYLES: Record<PatternStatus, string> = {
  draft: "bg-stone-100 text-stone-600",
  review: "bg-amber-50 text-amber-700",
  approved: "bg-emerald-50 text-emerald-700",
  deprecated: "bg-red-50 text-red-600",
};

export default function StatusBadge({ status }: { status: PatternStatus }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-md text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}
