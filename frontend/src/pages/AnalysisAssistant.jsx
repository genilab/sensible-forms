import { useMemo, useState } from "react";
import { analyzeData } from "../services/analysisAssistant.js";
import { getOrCreateSessionId } from "../services/session.js";

export default function AnalysisAssistant() {
  const sessionId = useMemo(() => getOrCreateSessionId("analysis_assistant_session_id"), []);
  const [messages, setMessages] = useState(() => [
    {
      role: "bot",
      text: "Paste a short dataset summary and I’ll return 3–5 insights."
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const canSend = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);

  async function onSend(e) {
    e?.preventDefault?.();
    if (!canSend) return;

    const dataSummary = input.trim();
    setInput("");
    setError("");

    setMessages((prev) => [...prev, { role: "user", text: dataSummary }]);
    setIsLoading(true);

    try {
      const res = await analyzeData(dataSummary, sessionId);
      setMessages((prev) => [...prev, { role: "bot", text: res.insights }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section aria-labelledby="analysis-assistant-title">
      <h2 className="pageHeading" id="analysis-assistant-title">
        Analysis Assistant
      </h2>

      <div className="chat" aria-live="polite" aria-label="Analysis assistant conversation">
        {messages.map((m, idx) => (
          <div key={idx} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>

      <hr />

      <form onSubmit={onSend} className="row">
        <label htmlFor="analysis-assistant-input" className="sr-only">
          Enter a dataset summary
        </label>
        <input
          id="analysis-assistant-input"
          className="input"
          value={input}
          placeholder='Example: "N=42. Satisfaction avg 3.8/5. Drop-off after Q6."'
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button className="button" type="submit" disabled={!canSend}>
          {isLoading ? "Analyzing…" : "Send"}
        </button>
      </form>

      {error ? (
        <div className="alert" role="alert">
          Error: {error}
        </div>
      ) : null}
    </section>
  );
}