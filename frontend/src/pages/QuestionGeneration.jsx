/**
 * QuestionGeneration.jsx
 *
 * Screen component responsible for:
 * - Accepting input from the user
 * - Requesting AI-generated survey questions
 * - (Perhaps) Rendering the generated question list
 *
 * This page coordinates user interaction
 * but delegates data fetching to services.
 */

// Example Code:
import { useMemo, useState } from "react";

import { generateQuestions } from "../services/questionGenerationService.js";

export default function QuestionGeneration() {
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text: "Tell me a topic and I’ll brainstorm survey questions. (Example-only; file upload parsing is future work.)"
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
			const res = await generateQuestions(topic);
			const formatted = res.questions.map((q) => `- ${q}`).join("\n");
			setMessages((prev) => [...prev, { role: "bot", text: formatted }]);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsLoading(false);
		}
	}

	return (
		<div>
			<div style={{ fontWeight: 700, marginBottom: 8 }}>Question Generation</div>
			<div className="small" style={{ marginBottom: 12 }}>
				Calls <code>POST /question-generation/</code> → domain service → agent → LLM client.
			</div>

			<div className="chat" aria-live="polite">
				{messages.map((m, idx) => (
					<div key={idx} className={`msg ${m.role}`}>{m.text}</div>
				))}
			</div>

			<hr />

			<form onSubmit={onSend} className="row">
				<input
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
				<div className="small" style={{ marginTop: 8 }}>
					Error: {error}
				</div>
			) : null}
		</div>
	);
}