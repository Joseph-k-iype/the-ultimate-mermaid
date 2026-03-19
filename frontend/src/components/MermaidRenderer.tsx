import { useEffect, useRef, useState, useCallback } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
  flowchart: { htmlLabels: true, curve: "basis" },
  er: { useMaxWidth: true },
});

let renderCounter = 0;

/**
 * Sanitize mermaid code to fix common issues that cause rendering failures.
 */
function sanitizeMermaidCode(code: string): string {
  let sanitized = code;

  // Remove lines with unbalanced quotes in labels
  sanitized = sanitized
    .split("\n")
    .map((line) => {
      // Fix lines with odd number of double quotes (unbalanced)
      const quoteCount = (line.match(/"/g) || []).length;
      if (quoteCount % 2 !== 0) {
        // Try to fix by escaping the last unbalanced quote
        const lastQuoteIdx = line.lastIndexOf('"');
        return (
          line.substring(0, lastQuoteIdx) +
          "#quot;" +
          line.substring(lastQuoteIdx + 1)
        );
      }
      return line;
    })
    .join("\n");

  // Replace problematic characters in node IDs (not inside quotes)
  // Mermaid IDs can't start with numbers or contain certain chars
  sanitized = sanitized.replace(
    /^(\s*)([\d])/gm,
    "$1n_$2"
  );

  return sanitized;
}

/**
 * Generate a simplified fallback version of the diagram
 * by stripping complex syntax elements.
 */
function simplifyMermaidCode(code: string): string {
  const lines = code.split("\n");
  if (lines.length === 0) return code;

  const header = lines[0].trim();
  const simplified: string[] = [header];

  // For flowcharts, keep only simple node definitions and edges
  if (header.startsWith("flowchart") || header.startsWith("graph")) {
    for (const line of lines.slice(1)) {
      const trimmed = line.trim();
      // Keep subgraph/end, simple nodes, and edges
      if (
        trimmed.startsWith("subgraph") ||
        trimmed === "end" ||
        trimmed.includes("-->") ||
        trimmed.match(/^\w[\w_]*\[/) ||
        trimmed.match(/^\w[\w_]*\(\[/) ||
        trimmed.startsWith("%%")
      ) {
        // Simplify labels: replace complex label syntax with simple ones
        const simpleLine = trimmed
          .replace(/\(\["([^"]*?)"\]\)/g, '["$1"]')  // stadium → rect
          .replace(/\[\\?"([^"]*?)"\\?\]/g, '["$1"]')  // trapezoid → rect
          .replace(/\[\/"([^"]*?)"\/\]/g, '["$1"]')  // parallelogram → rect
          .replace(/\[\\?"([^"]*?)"\/\]/g, '["$1"]')  // trapezoid alt → rect
          .replace(/>\s*"([^"]*?)"\]/g, '["$1"]');  // asymmetric → rect
        simplified.push("    " + simpleLine);
      }
    }
    return simplified.join("\n");
  }

  // For erDiagram, keep entity blocks and relationships
  if (header === "erDiagram") {
    for (const line of lines.slice(1)) {
      const trimmed = line.trim();
      if (
        trimmed.startsWith("%%") ||
        trimmed.includes("||--") ||
        trimmed.includes("}o--") ||
        trimmed.includes("{") ||
        trimmed.includes("}") ||
        trimmed.match(/^\w+\s*\{/) ||
        trimmed.match(/^\s*(string|method|int|float)\s/) ||
        trimmed === ""
      ) {
        simplified.push(line);
      }
    }
    return simplified.join("\n");
  }

  return code;
}

/**
 * Truncate Mermaid code by keeping only the first N content lines.
 * Preserves the header and comment lines, and balances subgraphs and braces.
 */
function truncateMermaidCode(code: string, maxLines = 60): string {
  const lines = code.split("\n");
  if (lines.length <= maxLines) return code;

  const header = lines[0];
  const contentLines = lines.slice(1);

  // Keep subgraph structure intact: track open subgraphs and braces
  const kept: string[] = [header];
  let openSubgraphs = 0;
  let openBraces = 0;
  let contentCount = 0;

  for (const line of contentLines) {
    const trimmed = line.trim();

    // Always keep comments
    if (trimmed.startsWith("%%")) {
      kept.push(line);
      continue;
    }

    if (trimmed.startsWith("subgraph")) {
      openSubgraphs++;
      if (contentCount < maxLines) {
        kept.push(line);
        contentCount++;
      }
      continue;
    }

    if (trimmed === "end" && openSubgraphs > 0) {
      openSubgraphs--;
      kept.push(line);
      continue;
    }

    // Keep track of braces for namespaces and classes
    if (trimmed.endsWith("{")) {
      openBraces++;
    }
    if (trimmed === "}" && openBraces > 0) {
      openBraces--;
      kept.push(line);
      continue;
    }

    if (contentCount < maxLines) {
      kept.push(line);
      contentCount++;
    }
  }

  // Close any remaining open subgraphs and braces
  while (openSubgraphs > 0) {
    kept.push("    end");
    openSubgraphs--;
  }
  while (openBraces > 0) {
    kept.push("    }");
    openBraces--;
  }

  return kept.join("\n");
}

export default function MermaidRenderer({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryLevel, setRetryLevel] = useState(0);
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setScale(s => Math.min(Math.max(s * delta, 0.1), 5));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - translate.x, y: e.clientY - translate.y });
    }
  }, [translate]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      setTranslate({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
    }
  }, [isPanning, panStart]);

  const handleMouseUp = useCallback(() => setIsPanning(false), []);

  const resetView = useCallback(() => {
    setScale(1);
    setTranslate({ x: 0, y: 0 });
  }, []);

  useEffect(() => {
    if (!code || !containerRef.current) return;
    setError(null);
    setRetryLevel(0);
    setScale(1);
    setTranslate({ x: 0, y: 0 });

    const tryRender = async (
      mermaidCode: string,
      level: number
    ): Promise<boolean> => {
      try {
        const id = `mermaid-${++renderCounter}`;
        const { svg } = await mermaid.render(id, mermaidCode);
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
        return true;
      } catch {
        // Clean up any lingering error elements mermaid injects
        const errorEl = document.getElementById(`d${renderCounter}`);
        if (errorEl) errorEl.remove();

        if (level === 0) {
          // Level 1: try sanitized version
          setRetryLevel(1);
          return tryRender(sanitizeMermaidCode(mermaidCode), 1);
        }
        if (level === 1) {
          // Level 2: try simplified version
          setRetryLevel(2);
          return tryRender(simplifyMermaidCode(code), 2);
        }
        if (level === 2) {
          // Level 3: truncate to first 60 content lines
          setRetryLevel(3);
          return tryRender(truncateMermaidCode(simplifyMermaidCode(code), 60), 3);
        }
        return false;
      }
    };

    tryRender(code, 0).then((success) => {
      if (!success) {
        setError("Diagram could not be rendered");
      }
    });
  }, [code]);

  if (error) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-stone-500 text-sm">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>Diagram syntax could not be parsed — showing raw code</span>
        </div>
        <pre className="bg-stone-50 border border-stone-200 p-4 rounded-lg text-xs overflow-auto whitespace-pre-wrap text-stone-600 max-h-96">
          {code}
        </pre>
      </div>
    );
  }

  return (
    <div>
      {retryLevel > 0 && (
        <p className="text-xs text-amber-600 mb-2">
          {retryLevel >= 3
            ? "Diagram was truncated for rendering compatibility"
            : "Diagram was auto-corrected for rendering compatibility"}
        </p>
      )}
      <div className="relative border border-stone-200 rounded-xl overflow-hidden bg-white">
        {/* Toolbar */}
        <div className="absolute top-2 right-2 z-10 flex items-center gap-1 bg-white/95 border border-stone-200 rounded-lg shadow-sm p-1">
          <button onClick={() => setScale(s => Math.min(s * 1.2, 5))} className="p-1.5 rounded hover:bg-stone-100 text-stone-500" title="Zoom In">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <span className="text-[10px] text-stone-400 w-8 text-center">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.max(s * 0.8, 0.1))} className="p-1.5 rounded hover:bg-stone-100 text-stone-500" title="Zoom Out">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          <div className="w-px h-4 bg-stone-200 mx-0.5" />
          <button onClick={resetView} className="p-1.5 rounded hover:bg-stone-100 text-stone-500 text-[10px] font-medium" title="Reset View">
            Fit
          </button>
        </div>
        {/* Pannable/zoomable container */}
        <div
          className="overflow-hidden cursor-grab active:cursor-grabbing"
          style={{ height: "500px" }}
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
              transition: isPanning ? "none" : "transform 0.1s ease",
            }}
          />
        </div>
      </div>
    </div>
  );
}
