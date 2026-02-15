/**
 * App.jsx
 *
 * Minimal shell that unifies the three LLM-powered workflows behind one UI.
 * This intentionally avoids extra dependencies (no router) for a first-commit example.
 */

// Example Code:
import { useMemo, useState } from "react";

import AnalysisAssistant from "./pages/AnalysisAssistant.jsx";
import QuestionGeneration from "./pages/QuestionGeneration.jsx";
import FormDeployment from "./pages/FormDeployment.jsx";

const PAGES = {
  questionGeneration: {
    label: "Question Generation",
    Component: QuestionGeneration
  },
  analysisAssistant: {
    label: "Analysis Assistant",
    Component: AnalysisAssistant
  },
  formDeployment: {
    label: "Form Deployment",
    Component: FormDeployment
  }
};

export default function App() {
  const [active, setActive] = useState("questionGeneration");

  const ActiveComponent = useMemo(() => PAGES[active].Component, [active]);

  return (
    <div className="container">
      <div className="topbar">
        <div>
          <div style={{ fontWeight: 700 }}>SensibleForms (Example UI)</div>
          <div className="small">
            Demonstrates frontend → FastAPI → domain service → agent → LLM client
          </div>
        </div>

        <div className="nav" role="tablist" aria-label="Bots">
          {Object.entries(PAGES).map(([key, value]) => (
            <button
              key={key}
              type="button"
              className="button"
              aria-pressed={active === key}
              onClick={() => setActive(key)}
            >
              {value.label}
            </button>
          ))}
        </div>
      </div>

      <div className="panel">
        <ActiveComponent />
      </div>

      <div className="small" style={{ marginTop: 10 }}>
        Backend default: <code>http://localhost:8000</code> (override with <code>VITE_API_BASE_URL</code>)
      </div>
    </div>
  );
}
