import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type ScanRequest } from "../api/client";

interface Props {
  onScanComplete: (scanId: string) => void;
}

export default function ScanForm({ onScanComplete }: Props) {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");

  const mutation = useMutation({
    mutationFn: (req: ScanRequest) => api.startScan(req),
    onSuccess: (data) => onScanComplete(data.scan_id),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    mutation.mutate({ repo_url: repoUrl.trim(), branch: branch.trim() || "main" });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-stone-600 mb-1">
          Repository URL
        </label>
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/user/repo.git"
          className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-stone-600 mb-1">
          Branch
        </label>
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="main"
          className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-400"
        />
      </div>
      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full bg-stone-900 text-white py-2 px-4 rounded-lg hover:bg-stone-800 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {mutation.isPending ? "Scanning..." : "Scan Repository"}
      </button>
      {mutation.isError && (
        <p className="text-red-500 text-sm">{mutation.error.message}</p>
      )}
    </form>
  );
}
