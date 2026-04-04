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
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { analyzeData, uploadAnalysisCsv } from "../services/analysisAssistant.js";
import { getOrCreateSessionId } from "../services/session.js";

export default function AnalysisAssistant() {
	const sessionId = useMemo(() => getOrCreateSessionId("analysis_assistant_session_id"), []);
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text: "Upload a question and response CSV to create a survey dataset for analysis assistance. Or, simply type a summary of your dataset and I’ll provide insights or suggestions for further analysis."
		}
	]);
	const [input, setInput] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [isUploading, setIsUploading] = useState(false);
	const [selectedFile, setSelectedFile] = useState(null);
	const [error, setError] = useState("");

	const canSend = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);
	const canUpload = useMemo(
		() => !!selectedFile && !isUploading,
		[selectedFile, isUploading]
	);

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

	async function onUploadCsv() {
		if (!canUpload) return;
		setError("");
		setIsUploading(true);
		try {
			const res = await uploadAnalysisCsv(selectedFile, sessionId);
			setMessages((prev) => [...prev, { role: "bot", text: res.insights }]);
			setSelectedFile(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsUploading(false);
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
					<div key={idx} className={`msg ${m.role}`}>
						{m.role === "bot" ? (
							<div className="md">
								<ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
							</div>
						) : (
							m.text
						)}
					</div>
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

			<div style={{ marginTop: 12 }}>
				<div className="small" style={{ marginBottom: 6 }}>
					Upload CSV (ingests into analysis session):
				</div>
				<div className="row">
					<input
						className="input"
						type="file"
						accept=".csv"
						onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
						disabled={isUploading}
					/>
					<button
						className="button"
						type="button"
						disabled={!canUpload}
						onClick={onUploadCsv}
					>
						{isUploading ? "Uploading…" : "Upload CSV"}
					</button>
				</div>
			</div>

			{error ? (
				<div className="small" style={{ marginTop: 8 }}>
					Error: {error}
				</div>
			) : null}
		</div>
	);
}
