import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Dashboard from "./pages/Dashboard";
import DiagramPage from "./pages/DiagramPage";
import TemplatePage from "./pages/TemplatePage";
import PatternLibraryPage from "./pages/PatternLibraryPage";
import PatternDetailPage from "./pages/PatternDetailPage";
import PatternEditorPage from "./pages/PatternEditorPage";
import KnowledgeGraphPage from "./pages/KnowledgeGraphPage";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-stone-50/50">
          <nav className="bg-white/80 backdrop-blur-xl border-b border-stone-200/50 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center gap-8">
              <Link to="/" className="text-lg font-bold text-stone-900 tracking-tighter">
                Pattern<span className="text-stone-400">Viz</span>
              </Link>
              <Link
                to="/"
                className="text-[13px] font-medium text-stone-500 hover:text-stone-900 transition-colors duration-200"
              >
                Dashboard
              </Link>
              <Link
                to="/templates"
                className="text-[13px] font-medium text-stone-500 hover:text-stone-900 transition-colors duration-200"
              >
                Templates
              </Link>
              <Link
                to="/patterns"
                className="text-[13px] font-medium text-stone-500 hover:text-stone-900 transition-colors duration-200"
              >
                Pattern Library
              </Link>
              <Link
                to="/knowledge-graph"
                className="text-[13px] font-medium text-stone-500 hover:text-stone-900 transition-colors duration-200"
              >
                Knowledge Graph
              </Link>
            </div>
          </nav>
          <main className="py-6 px-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/scan/:scanId" element={<DiagramPage />} />
              <Route path="/templates" element={<TemplatePage />} />
              <Route path="/patterns" element={<PatternLibraryPage />} />
              <Route path="/patterns/new" element={<PatternEditorPage />} />
              <Route path="/patterns/:patternId" element={<PatternDetailPage />} />
              <Route path="/patterns/:patternId/edit" element={<PatternEditorPage />} />
              <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
