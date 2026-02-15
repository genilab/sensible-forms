/**
 * AnalysisAssistant.jsx
 *
 * Screen component responsible for:
 * - Rendering the dataset analysis interface
 * - Collecting user-provided dataset summaries
 * - Triggering analysis API requests
 * - Displaying structured analysis results
 *
 * This component should remain presentation-focused.
 * Business logic should live in services or hooks.
 */

// Example Code:
import { useMemo, useState } from "react";

import { analyzeData } from "../services/analysisAssistant.js";

export default function AnalysisAssistant() {
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text: "Paste a short dataset summary and I’ll return 3–5 insights. (Example-only; no file parsing here yet.)"
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
			const res = await analyzeData(dataSummary);
			setMessages((prev) => [...prev, { role: "bot", text: res.insights }]);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsLoading(false);
		}
	}

	return (
		<div>
			<div style={{ fontWeight: 700, marginBottom: 8 }}>Analysis Assistant</div>
			<div className="small" style={{ marginBottom: 12 }}>
				Calls <code>POST /analysis/</code> → domain service → agent → LLM client.
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
					placeholder='Example: "N=42. Satisfaction avg 3.8/5. Drop-off after Q6."'
					onChange={(e) => setInput(e.target.value)}
					disabled={isLoading}
				/>
				<button className="button" type="submit" disabled={!canSend}>
					{isLoading ? "Analyzing…" : "Send"}
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
