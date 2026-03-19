import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import type { DetectedPattern } from "../../types/agents";

let diagramCounter = 0;

interface PatternDiagramsProps {
  patterns: DetectedPattern[];
}

export default function PatternDiagrams({ patterns }: PatternDiagramsProps) {
  const diagramPatterns = patterns.filter((p) => p.pattern_type.startsWith("diagram:"));

  if (diagramPatterns.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-stone-800 tracking-tight">
        AI-Generated Diagrams
      </h3>
      {diagramPatterns.map((pattern, i) => (
        <DiagramCard key={i} pattern={pattern} />
      ))}
    </div>
  );
}

function DiagramCard({ pattern }: { pattern: DetectedPattern }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  const mermaidCode = pattern.related_perspectives?.[0] || "";
  const title = pattern.description || "Diagram";

  useEffect(() => {
    if (!mermaidCode || !containerRef.current) return;
    setError(false);
    setScale(1);
    setTranslate({ x: 0, y: 0 });

    const render = async () => {
      try {
        const id = `ai-diagram-${++diagramCounter}`;
        const { svg } = await mermaid.render(id, mermaidCode);
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch {
        // Try to clean up
        const el = document.getElementById(`d${diagramCounter}`);
        if (el) el.remove();
        setError(true);
      }
    };
    render();
  }, [mermaidCode]);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setScale((s) => Math.min(Math.max(s * (e.deltaY > 0 ? 0.9 : 1.1), 0.1), 5));
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - translate.x, y: e.clientY - translate.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setTranslate({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
    }
  };

  const handleMouseUp = () => setIsPanning(false);

  if (!mermaidCode) return null;

  return (
    <div className="bg-white rounded-2xl border border-stone-200/60 overflow-hidden shadow-sm transition-shadow hover:shadow-md">
      <div className="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
        <span className="text-xs font-semibold text-stone-700 tracking-tight">{title}</span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setScale((s) => Math.min(s * 1.2, 5))}
            className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-stone-100 text-stone-400 transition-colors"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <span className="text-[10px] text-stone-400 font-mono w-8 text-center">{Math.round(scale * 100)}%</span>
          <button
            onClick={() => setScale((s) => Math.max(s * 0.8, 0.1))}
            className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-stone-100 text-stone-400 transition-colors"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <button
            onClick={() => { setScale(1); setTranslate({ x: 0, y: 0 }); }}
            className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-stone-100 text-stone-400 text-[10px] font-semibold transition-colors"
          >
            Fit
          </button>
        </div>
      </div>
      {error ? (
        <div className="p-4">
          <pre className="text-[11px] text-stone-500 bg-stone-50 rounded-xl p-3 overflow-auto max-h-48 font-mono">{mermaidCode}</pre>
        </div>
      ) : (
        <div
          className="overflow-hidden cursor-grab active:cursor-grabbing"
          style={{ height: "320px" }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <div
            ref={containerRef}
            style={{
              transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
              transformOrigin: "0 0",
              transition: isPanning ? "none" : "transform 0.15s ease",
            }}
          />
        </div>
      )}
    </div>
  );
}
