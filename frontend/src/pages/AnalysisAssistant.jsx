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

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { chatAnalysis, uploadSurveyCsv } from "../services/analysisAssistant.js";
import { getOrCreateSessionId } from "../services/session.js";

export default function AnalysisAssistant() {
	const sessionId = useMemo(() => getOrCreateSessionId("analysis_assistant_session_id"), []);
	const [activeFileId, setActiveFileId] = useState("");
	const [selectedFile, setSelectedFile] = useState(null);
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text: "You can chat with me right away (even before uploading). If you upload a Google Forms responses CSV, I can ground suggestions in your actual columns and compute basic exact stats."
		}
	]);
	const [input, setInput] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");

	const canSend = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);

	async function onSend(e) {
		e?.preventDefault?.();
		if (!canSend) return;

		const userText = input.trim();
		setInput("");
		setError("");

		setMessages((prev) => [...prev, { role: "user", text: userText }]);
		setIsLoading(true);
		try {
			const res = await chatAnalysis({
				message: userText,
				session_id: sessionId,
				file_id: activeFileId || undefined,
				upload_mode: false
			});
			setMessages((prev) => [...prev, { role: "bot", text: res.message }]);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsLoading(false);
		}
	}

	async function onUpload(e) {
		e?.preventDefault?.();
		setError("");
		if (!selectedFile) return;

		setIsLoading(true);
		try {
			const up = await uploadSurveyCsv(selectedFile);
			setActiveFileId(up.file_id);
			setMessages((prev) => [
				...prev,
				{ role: "user", text: `Uploaded: ${up.filename}` }
			]);

			const res = await chatAnalysis({
				message: "",
				session_id: sessionId,
				file_id: up.file_id,
				upload_mode: true
			});
			setMessages((prev) => [...prev, { role: "bot", text: res.message }]);
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
				<input
					className="input"
					value={input}
					placeholder='Ask: "Summarize the dataset" or "What should I analyze next?"'
					onChange={(e) => setInput(e.target.value)}
					disabled={isLoading}
				/>
				<button className="button" type="submit" disabled={!canSend}>
					{isLoading ? "Analyzing…" : "Send"}
				</button>
			</form>

			<form onSubmit={onUpload} className="row" style={{ marginTop: 12 }}>
				<input
					className="input"
					type="file"
					accept=".csv,text/csv"
					onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
					disabled={isLoading}
				/>
				<button className="button" type="submit" disabled={!selectedFile || isLoading}>
					{isLoading ? "Uploading…" : "Upload CSV"}
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