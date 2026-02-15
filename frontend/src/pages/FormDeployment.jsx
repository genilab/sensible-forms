/**
 * FormDeployment.jsx
 *
 * Screen component responsible for:
 * - Triggering form deployment
 * - Displaying deployment status or results
 *
 * This component handles UI state only.
 * API communication should be delegated to services.
 */

// Example Code:
import { useMemo, useState } from "react";

import { sendDeploymentMessage, deploySurveyCsv } from "../services/formDeploymentService.js";

export default function FormDeployment() {
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text:
				"Upload your academic survey CSV, then chat with me about status (did it deploy?) or feedback (what needs fixing before deployment)."
		}
	]);
	const [input, setInput] = useState("");
	const [isSending, setIsSending] = useState(false);
	const [isDeploying, setIsDeploying] = useState(false);
	const [error, setError] = useState("");
	const [selectedFile, setSelectedFile] = useState(null);
	const [lastDeployFilename, setLastDeployFilename] = useState(null);
	const [lastDeployStatus, setLastDeployStatus] = useState(null);
	const [lastDeployFeedback, setLastDeployFeedback] = useState(null);

	const canSend = useMemo(() => input.trim().length > 0 && !isSending, [input, isSending]);
	const canDeploy = useMemo(() => selectedFile && !isDeploying, [selectedFile, isDeploying]);

	async function onSend(e) {
		e?.preventDefault?.();
		if (!canSend) return;

		const message = input.trim();
		setInput("");
		setError("");
		setMessages((prev) => [...prev, { role: "user", text: message }]);

		setIsSending(true);
		try {
			const res = await sendDeploymentMessage(message, {
				last_deploy_filename: lastDeployFilename,
				last_deploy_status: lastDeployStatus,
				last_deploy_feedback: lastDeployFeedback
			});
			setMessages((prev) => [...prev, { role: "bot", text: res.message }]);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsSending(false);
		}
	}

	async function onDeployUpload() {
		if (!canDeploy) return;
		setError("");
		setIsDeploying(true);
		try {
			const res = await deploySurveyCsv(selectedFile);
			setMessages((prev) => [
				...prev,
				{
					role: "bot",
					text: `Deterministic deploy: ${res.status}\n${res.feedback}`
				}
			]);
			setLastDeployFilename(res.filename);
			setLastDeployStatus(res.status);
			setLastDeployFeedback(res.feedback);
			setSelectedFile(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsDeploying(false);
		}
	}

	return (
		<div>
			<div style={{ fontWeight: 700, marginBottom: 8 }}>Form Deployment</div>
			<div className="small" style={{ marginBottom: 12 }}>
				Deploy calls <code>POST /form-deployment/deploy</code>. Chat calls <code>POST /form-deployment/chat</code>.
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
					placeholder='Try: "Did it deploy?" or "What should I fix before deployment?"'
					onChange={(e) => setInput(e.target.value)}
					disabled={isSending}
				/>
				<button className="button" type="submit" disabled={!canSend}>
					{isSending ? "Sending…" : "Send"}
				</button>
			</form>

			<div style={{ marginTop: 12 }}>
				<div className="small" style={{ marginBottom: 6 }}>
					Deploy your survey CSV (CSV only):
				</div>
				<div className="row">
					<input
						className="input"
						type="file"
						accept=".csv"
						onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
						disabled={isDeploying}
					/>
					<button className="button" type="button" disabled={!canDeploy} onClick={onDeployUpload}>
						{isDeploying ? "Deploying…" : "Deploy"}
					</button>
				</div>
			</div>

			{lastDeployFilename ? (
				<div className="small" style={{ marginTop: 8 }}>
					Last deploy: <code>{lastDeployFilename}</code> ({lastDeployStatus})
				</div>
			) : null}

			{error ? (
				<div className="small" style={{ marginTop: 8 }}>
					Error: {error}
				</div>
			) : null}
		</div>
	);
}
