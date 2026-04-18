import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { generateQuestions } from "../services/questionGenerationService.js";
import { getOrCreateSessionId } from "../services/session.js";

export default function QuestionGeneration() {
  const sessionId = useMemo(() => getOrCreateSessionId("question_generation_session_id"), []);
  const [messages, setMessages] = useState(() => [
    {
      role: "bot",
      text: "Tell me a topic and I’ll brainstorm survey questions."
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const canSend = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);

  async function onSend(e) {
    e?.preventDefault?.();
    if (!canSend) return;

    const topic = input.trim();
    setInput("");
    setError("");

    setMessages((prev) => [...prev, { role: "user", text: topic }]);
    setIsLoading(true);

    try {
      const res = await generateQuestions(topic, sessionId);
      const formatted = res.questions.map((q) => `- ${q}`).join("\n");
      setMessages((prev) => [...prev, { role: "bot", text: formatted }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section aria-labelledby="question-generation-title">
      <h2 className="pageHeading" id="question-generation-title">
        Question Generation
      </h2>

			<div className="chat" aria-live="polite">
				{messages.map((m, idx) => (
					<div key={idx} className={`msg ${m.role}`}>
						{m.role === "bot" ? (
							<ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
						) : (
							m.text
						)}
					</div>
				))}
			</div>

      <hr />

      <form onSubmit={onSend} className="row">
        <label htmlFor="question-generation-input" className="sr-only">
          Enter a survey topic
        </label>
        <input
          id="question-generation-input"
          className="input"
          value={input}
          placeholder='Example: "Employee engagement"'
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button className="button" type="submit" disabled={!canSend}>
          {isLoading ? "Thinking…" : "Send"}
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