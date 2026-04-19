import { useMemo, useState } from "react";
import logo from "./assets/placeholder-logo.png";

import AnalysisAssistant from "./pages/AnalysisAssistant.jsx";
import QuestionGeneration from "./pages/QuestionGeneration.jsx";
import FormDeployment from "./pages/FormDeployment.jsx";

const PAGES = {
  questionGeneration: { label: "Question Generation", Component: QuestionGeneration, icon: "💭" },
  formDeployment: { label: "Form Deployment", Component: FormDeployment, icon: "🚀" },
  analysisAssistant: { label: "Analysis Assistant", Component: AnalysisAssistant, icon: "📊" }
};

export default function App() {
  const [active, setActive] = useState("questionGeneration");
  const ActiveComponent = useMemo(() => PAGES[active].Component, [active]);

  return (
    <div className="container">
      <div className="shell">
        {/* Header */}
        <div className="topbar">
          <div className="brand">
            <img src={logo} alt="SensibleForms logo placeholder" className="logo" />
            <div>
              <div className="brandTitle">SensibleForms</div>
              <div className="brandSub">
                LLM-powered workflows for survey creation, analysis, and deployment
              </div>
            </div>
          </div>

        </div>

        {/* Sidebar + content */}
        <div className="layout">
          <aside className="sidebar" aria-label="Navigation">
            <div className="sidebarSectionLabel">Workflows</div>

            <nav className="sidebarNav" role="tablist" aria-label="Workflows">
              {Object.entries(PAGES).map(([key, value]) => (
                <button
                  key={key}
                  type="button"
                  className="sideItem"
                  aria-pressed={active === key}
                  onClick={() => setActive(key)}
                >
                  <span className="sideIcon" aria-hidden="true">
                    {value.icon}
                  </span>
                  <span className="sideLabel">{value.label}</span>
                </button>
              ))}
            </nav>

            <div className="sidebarFooter small">
              Backend: <code>http://localhost:8000</code>
              <div style={{ marginTop: 6 }}>
                Env: <code>VITE_API_BASE_URL</code>
              </div>
            </div>
          </aside>

          <main className="content">
            <div className="card">
              <ActiveComponent />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}