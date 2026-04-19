import { useEffect, useMemo, useState } from "react";
import logo from "./assets/NEWSensibleFormsIcon.png";

import AnalysisAssistant from "./pages/AnalysisAssistant.jsx";
import QuestionGeneration from "./pages/QuestionGeneration.jsx";
import FormDeployment from "./pages/FormDeployment.jsx";

const PAGES = {
  questionGeneration: {
    label: "Question Generation",
    Component: QuestionGeneration,
    icon: "💭"
  },
  formDeployment: {
    label: "Form Deployment",
    Component: FormDeployment,
    icon: "🚀"
  },
  analysisAssistant: {
    label: "Analysis Assistant",
    Component: AnalysisAssistant,
    icon: "📊"
  }
};

export default function App() {
  const [active, setActive] = useState("questionGeneration");
  const [largeText, setLargeText] = useState(false);
  const [highContrast, setHighContrast] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [lineSpacing, setLineSpacing] = useState(false);
  const [largeTargets, setLargeTargets] = useState(false);
  const [showAccessibility, setShowAccessibility] = useState(false);

  const ActiveComponent = useMemo(() => PAGES[active].Component, [active]);

  useEffect(() => {
    const savedLargeText = localStorage.getItem("sf_large_text") === "true";
    const savedHighContrast = localStorage.getItem("sf_high_contrast") === "true";
    const savedReduceMotion = localStorage.getItem("sf_reduce_motion") === "true";
    const savedDarkMode = localStorage.getItem("sf_dark_mode") === "true";
    const savedLineSpacing = localStorage.getItem("sf_line_spacing") === "true";
    const savedLargeTargets = localStorage.getItem("sf_large_targets") === "true";

    setLargeText(savedLargeText);
    setHighContrast(savedHighContrast);
    setReduceMotion(savedReduceMotion);
    setDarkMode(savedDarkMode);
    setLineSpacing(savedLineSpacing);
    setLargeTargets(savedLargeTargets);
  }, []);

  useEffect(() => {
    localStorage.setItem("sf_large_text", String(largeText));
  }, [largeText]);

  useEffect(() => {
    localStorage.setItem("sf_high_contrast", String(highContrast));
  }, [highContrast]);

  useEffect(() => {
    localStorage.setItem("sf_reduce_motion", String(reduceMotion));
  }, [reduceMotion]);

  useEffect(() => {
    localStorage.setItem("sf_dark_mode", String(darkMode));
  }, [darkMode]);

  useEffect(() => {
    localStorage.setItem("sf_line_spacing", String(lineSpacing));
  }, [lineSpacing]);

  useEffect(() => {
    localStorage.setItem("sf_large_targets", String(largeTargets));
  }, [largeTargets]);

  const accessibilityClasses = [
    largeText ? "large-text" : "",
    highContrast ? "high-contrast" : "",
    reduceMotion ? "reduce-motion" : "",
    darkMode ? "dark-mode" : "",
    lineSpacing ? "line-spacing" : "",
    largeTargets ? "large-targets" : ""
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={`container app-shell ${accessibilityClasses}`}>
      <div className="shell">
        <div className="topbar">
          <div className="brand">
            <img src={logo} alt="SensibleForms logo" className="logo" />
            <div>
              <h1 className="brandTitle">SensibleForms</h1>
              <p className="brandSub">
                LLM-powered workflows for survey creation, analysis, and deployment
              </p>
              <p className="startupNotice">
                Note: First request may take up to ~60 seconds due to server startup. After that, responses are fast.
              </p>
            </div>
          </div>
        </div>

        <div className="layout">
          <aside className="sidebar" aria-label="Application sidebar">
            <div className="sidebarSectionLabel">Workflows</div>

            <nav className="sidebarNav" aria-label="Workflows">
              {Object.entries(PAGES).map(([key, value]) => (
                <button
                  key={key}
                  type="button"
                  className="sideItem"
                  aria-pressed={active === key}
                  aria-current={active === key ? "page" : undefined}
                  onClick={() => setActive(key)}
                >
                  <span className="sideIcon" aria-hidden="true">
                    {value.icon}
                  </span>
                  <span className="sideLabel">{value.label}</span>
                </button>
              ))}
            </nav>

            <div className="sidebarFooter">
              <button
                type="button"
                className="accessibilityToggleButton"
                aria-expanded={showAccessibility}
                aria-controls="accessibility-panel"
                onClick={() => setShowAccessibility((prev) => !prev)}
              >
                <span className="sidebarSectionLabel accessibilityHeading">
                  Accessibility
                </span>
                <span className="accessibilityChevron" aria-hidden="true">
                  {showAccessibility ? "▾" : "▸"}
                </span>
              </button>

              {showAccessibility && (
                <div className="accessibilityControls" id="accessibility-panel">
                  <label className="toggleRow">
                    <input
                      type="checkbox"
                      checked={largeText}
                      onChange={(e) => setLargeText(e.target.checked)}
                    />
                    <span>Large Text</span>
                  </label>

                  <label className="toggleRow">
                    <input
                      type="checkbox"
                      checked={highContrast}
                      onChange={(e) => setHighContrast(e.target.checked)}
                    />
                    <span>High Contrast</span>
                  </label>

                  <label className="toggleRow">
                    <input
                      type="checkbox"
                      checked={reduceMotion}
                      onChange={(e) => setReduceMotion(e.target.checked)}
                    />
                    <span>Reduced Motion</span>
                  </label>

                  <label className="toggleRow">
                    <input
                      type="checkbox"
                      checked={darkMode}
                      onChange={(e) => setDarkMode(e.target.checked)}
                    />
                    <span>Dark Mode</span>
                  </label>

                  <label className="toggleRow">
                    <input
                      type="checkbox"
                      checked={lineSpacing}
                      onChange={(e) => setLineSpacing(e.target.checked)}
                    />
                    <span>Increased Line Spacing</span>
                  </label>

                  <label className="toggleRow">
                    <input
                      type="checkbox"
                      checked={largeTargets}
                      onChange={(e) => setLargeTargets(e.target.checked)}
                    />
                    <span>Larger Click Targets</span>
                  </label>
                </div>
              )}
            </div>
          </aside>

          <main className="content" id="main-content">
            <div className="card">
              <ActiveComponent />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}