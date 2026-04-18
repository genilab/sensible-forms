/**
 * QuestionGeneration.jsx
 * 
 * Copilot was used to assist with the creation of this code.
 *
 * Screen component responsible for:
 * - Accepting input from the user
 * - Requesting AI-generated survey questions
 * - Downloading the generated question list as a CSV
 *
 * This page coordinates user interaction but delegates data fetching to services.
 */

// Imports
import { useMemo, useState } from "react";
import { generateQuestions } from "../services/questionGenerationService.js";
import { getOrCreateSessionId } from "../services/session.js";

// Function for user interaction with the LLM
export default function QuestionGeneration() {
	// Setting the initial states
	const sessionId = useMemo(() => getOrCreateSessionId("question_generation_session_id"), []);
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text: "Tell me a topic and I’ll help you brainstorm survey questions."
		}
	]);
	const [input, setInput] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");
	const [isDownloading, setIsDownloading] = useState(false);
	const [lastResponse, setLastResponse] = useState("")

  const canSend = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);

	// Sending messages to and receiving messages from the LLM
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
			// Saves the last LLM response
			setLastResponse(res.questions)
			// Formatting the LLM response
			const formatted = res.questions.map((q) => `${q}`).join("\n\n");
			setMessages((prev) => [...prev, { role: "bot", text: formatted }]);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsLoading(false);
		}

	}

	// Extracts the relevant CSV information from an LLM response
	function extractStructuredCsv(text) {
		const lines = text.split("\n").map(l => l.trim());

		const csvLines = lines.filter(line => line.includes((line.match(/Q\d+,|question_id,/))));
		if (!csvLines.length) return [];

		const expectedColumns = csvLines[0].split(",").length;
		

		return csvLines.filter(
			line => line.split(",").length === expectedColumns
		);
	}

	// Downloads a CSV file of the last LLM response
	async function onDownloadCSV() {
		setIsDownloading(true);
		setError("");
		// Extracting the last LLM response and converting it to a CSV file
		//	The CSV file is automatically downloaded after generation
		try {
			console.log("Last LLM Response", lastResponse);
			const csvLines = lastResponse.flatMap(text => extractStructuredCsv(text));
			console.log("Extracted CSV lines", csvLines);

			const csv = csvLines.join("\n");
			const blob = new Blob(["\ufeff" + csv], { type: 'text/csv;charset=utf-8;' });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = "questions.csv";
			document.body.appendChild(link);
			link.click();
			link.remove();
			URL.revokeObjectURL(url);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			setIsDownloading(false);
		}
	}

  return (
    <section aria-labelledby="question-generation-title">
      <h2 className="pageHeading" id="question-generation-title">
        Question Generation
      </h2>

      <div className="chat" aria-live="polite" aria-label="Question generation conversation">
        {messages.map((m, idx) => (
          <div key={idx} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>

			{/*This button is for submitting the user message.*/}
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

			{/*This button is for downloading a CSV of the last LLM response.*/}
			<div style={{ marginTop: 24, borderTop: '1px solid #eee', pt: 12}}>
				<div className="small" style={{ marginBottom: 6 }}>
					Create CSV of the last response
				</div>
				<button
					className="button"
					type="button"
					disabled={isDownloading}
					onClick={onDownloadCSV}
				>
					{isDownloading ? "Getting Question CSV..." : "Download CSV"}
				</button>
			</div>

			{error ? (
				<div className="small" style={{ marginTop: 8 }}>
					Error: {error}
				</div>
			) : null}
		</section>
	);
}