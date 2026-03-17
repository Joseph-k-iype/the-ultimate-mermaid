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
        <div className="min-h-screen bg-stone-50">
          <nav className="bg-white border-b border-stone-200">
            <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-6">
              <Link to="/" className="text-lg font-bold text-stone-900 tracking-tight">
                PatternViz
              </Link>
              <Link
                to="/"
                className="text-sm text-stone-500 hover:text-stone-900"
              >
                Dashboard
              </Link>
              <Link
                to="/templates"
                className="text-sm text-stone-500 hover:text-stone-900"
              >
                Templates
              </Link>
              <Link
                to="/patterns"
                className="text-sm text-stone-500 hover:text-stone-900"
              >
                Pattern Library
              </Link>
              <Link
                to="/knowledge-graph"
                className="text-sm text-stone-500 hover:text-stone-900"
              >
                Knowledge Graph
              </Link>
            </div>
          </nav>
          <main className="py-8 px-4">
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
