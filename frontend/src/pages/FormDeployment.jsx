/*
 * FormDeployment.jsx
 *
 * Screen component responsible for:
 * - Triggering form deployment
 * - Displaying deployment status or results
 *
 * This component handles UI state only.
 * API communication should be delegated to services.
 */

import { useMemo, useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { sendDeploymentMessage, deployFormCsv, getFormResponses } from "../services/formDeploymentService.js";
import { getOrCreateSessionId } from "../services/session.js";
import { LoadingDots } from "../App.jsx"

export default function FormDeployment() {
	const sessionId = useMemo(() => getOrCreateSessionId("form_deployment_session_id"), []);
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text: "Upload your academic survey CSV, then chat with me about status (did it deploy?) or feedback (what needs fixing before deployment)."
		}
	]);
	const [input, setInput] = useState("");
	const [isSending, setIsSending] = useState(false);
	const [selectedFile, setSelectedFile] = useState(null);
	const [isDeploying, setIsDeploying] = useState(false);
	const [formIdInput, setFormIdInput] = useState("");
	const [isDownloading, setIsDownloading] = useState(false);
	const [error, setError] = useState("");
	const [lastDeployFilename, setLastDeployFilename] = useState(null);
	const [lastDeployStatus, setLastDeployStatus] = useState(null);
	const [lastDeployFormId, setLastDeployFormId] = useState(null);
	const [lastDeployFeedback, setLastDeployFeedback] = useState(null);
	const [lastRetrieveFormId, setLastRetrieveFormId] = useState(null);
    const [lastRetrieveStatus, setLastRetrieveStatus] = useState(null);
    const [lastRetrieveFeedback, setLastRetrieveFeedback] = useState(null);

	const canSend = useMemo(() => input.trim().length > 0 && !isSending, [input, isSending]);
	const canDeploy = useMemo(() => selectedFile && !isDeploying, [selectedFile, isDeploying]);
	const fileInputRef = useRef(null)

	// Reset input box for file upload (patches a browser inconsistency)
	function resetFileInput() {
		setSelectedFile(null);
		if (fileInputRef.current) fileInputRef.current.value = "";
	}
  
	async function onSend(e) {
		e?.preventDefault?.();
		if (!canSend) return;
		const message = input.trim();
		setInput("");
		setError("");
		setMessages((prev) => [...prev, { role: "user", text: message }]);
		setIsSending(true);
		try {
			const res = await sendDeploymentMessage(message, sessionId, {
				last_deploy_filename: lastDeployFilename,
				last_deploy_status: lastDeployStatus,
				last_deploy_formId: lastDeployFormId,
				last_deploy_feedback: lastDeployFeedback,
				last_retrieve_formId: lastRetrieveFormId,
				last_retrieve_status: lastRetrieveStatus,
				last_retrieve_feedback: lastRetrieveFeedback
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
			const res = await deployFormCsv(selectedFile);
			setMessages((prev) => [
				...prev,
				{
					role: "bot",
					text: `Deterministic deploy: ${res.status}\n${res.feedback}`
				}
			]);
			setLastDeployFilename(res.filename);
			setLastDeployStatus(res.status);
			setLastDeployFormId(res.formId);
			setLastDeployFeedback(res.feedback);
			setSelectedFile(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsDeploying(false);
			resetFileInput()
		}
	}

	async function onDownloadCSV() {
		if (!formIdInput.trim()) return;
		setError("")
		setIsDownloading(true);
		try {
			const res = await getFormResponses(formIdInput);
			setMessages((prev) => [
				...prev,
				{
					role: "bot",
					text: `Deterministic retrieve: ${res.status}\n${res.feedback}`
				}
			]);
			if (res.status.trim() == "error") return;
			const csvContent = res.content;
			const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.setAttribute("href", url)
			link.setAttribute("download", `responses_${formIdInput}.csv`);
			link.click();
			URL.revokeObjectURL(url);
			setLastRetrieveFormId(res.formId);
			setLastRetrieveStatus(res.status);
			setLastRetrieveFeedback(res.feedback);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsDownloading(false);
		}
	}

  return (
    <section aria-labelledby="form-deployment-title">
		<h2 className="pageHeading" id="form-deployment-title">
			Form Deployment
		</h2>

		<div className="chat" aria-live="polite">
			{messages.map((m, idx) => (
				<div key={idx} className={`msg ${m.role}`}>
					{m.role === "bot" ? (
						<ReactMarkdown 
						className = "markdown"
						remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
					) : (
						m.text
					)}
				</div>
			))}
		</div>

		<hr />

		<form onSubmit={onSend} className="row">
			<label htmlFor="form-deployment-message" className="sr-only">
			Enter a deployment question or message
			</label>
			<input
			id="form-deployment-message"
			className="input"
			value={input}
			placeholder='Try: "Did it deploy?" or "What should I fix before deployment?"'
			onChange={(e) => setInput(e.target.value)}
			disabled={isSending}
			/>
			<button className="button" type="submit" disabled={!canSend}>
			{isSending ? <LoadingDots text = "Sending" active = {isSending} /> : "Send"}
			</button>
		</form>

		<div style={{ marginTop: 12 }}>
			<label htmlFor="csv-upload" className="small fileLabel">
			Deploy your survey CSV (CSV only):
			</label>
			<div className="row">
			<input
				id="csv-upload"
				className="input"
				ref={fileInputRef}
				type="file"
				accept=".csv"
				onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
				disabled={isDeploying}
			/>
			<button className="button" type="button" disabled={!canDeploy} onClick={onDeployUpload}>
				{isDeploying ? <LoadingDots text = "Deploying" active = {isDeploying} /> : "Deploy"}
			</button>
			</div>
		</div>

		{lastDeployFilename ? (
			<div className="small" style={{ marginTop: 8 }}>
				Last deploy: <code>{lastDeployFilename}</code> ({lastDeployStatus})
			</div>
		) : null}

      	<div style={{ marginTop: 12}}>
			<div className="small" style={{ marginBottom: 6 }}>
				Retrieve Form Responses (via Form ID):
			</div>
			<div className="row">
				<input
					className="input"
					placeholder="Enter Form ID..."
					value={formIdInput}
					onChange={(e) => setFormIdInput(e.target.value)}
					disabled={isDownloading}
				/>
				<button
					className="button"
					type="button"
					disabled={isDownloading || !formIdInput}
					onClick={onDownloadCSV}
				>
					{isDownloading ? <LoadingDots text = "Getting Response CSV" active = {isDownloading} /> : "Download CSV"}
				</button>
			</div>
		</div>

		{error ? (
			<div className="alert" role="alert">
				Error: {error}
			</div>
		) : null}
		</section>
	);
}
