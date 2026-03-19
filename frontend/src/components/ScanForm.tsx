import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import gsap from "gsap";
import { api, type ScanRequest } from "../api/client";

interface Props {
  onScanComplete: (scanId: string) => void;
}

export default function ScanForm({ onScanComplete }: Props) {
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (formRef.current) {
      gsap.fromTo(
        formRef.current.children,
        { opacity: 0, x: -8 },
        { opacity: 1, x: 0, duration: 0.35, stagger: 0.06, ease: "power2.out" }
      );
    }
  }, []);

  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");

  const mutation = useMutation({
    mutationFn: (req: ScanRequest) => api.startScan(req),
    onSuccess: (data) => onScanComplete(data.scan_id),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    mutation.mutate({
      repo_url: repoUrl.trim(),
      branch: branch.trim() || "main",
    });
  };

  return (
    <form ref={formRef} onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-stone-600 mb-1">
          Repository URL
        </label>
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/user/repo.git"
          className="w-full px-4 py-2.5 border border-stone-200 rounded-xl bg-stone-50/50 focus:outline-none focus:ring-2 focus:ring-stone-900/10 focus:border-stone-400 transition-all duration-200 text-sm"
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
          className="w-full px-4 py-2.5 border border-stone-200 rounded-xl bg-stone-50/50 focus:outline-none focus:ring-2 focus:ring-stone-900/10 focus:border-stone-400 transition-all duration-200 text-sm"
        />
      </div>

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full bg-stone-900 text-white py-2.5 px-4 rounded-xl hover:bg-stone-800 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 text-sm font-medium shadow-sm"
      >
        {mutation.isPending ? "Scanning..." : "Scan Repository"}
      </button>
      {mutation.isError && (
        <p className="text-red-500 text-sm">{mutation.error.message}</p>
      )}
    </form>
  );
}
