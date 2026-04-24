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
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { generateQuestions } from "../services/questionGenerationService.js";
import { getOrCreateSessionId } from "../services/session.js";
import { LoadingDots } from "../App.jsx";

// Function for user interaction with the LLM
export default function QuestionGeneration() {
	// Setting the initial states
	const sessionId = useMemo(() => getOrCreateSessionId("question_generation_session_id"), []);
	const [messages, setMessages] = useState(() => [
		{
			role: "bot",
			text: "Tell me what you are researching and I’ll help you brainstorm survey questions."
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
			// Sends request to the LLM
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

	// Normalizes the last LLM response into a string
	function normalizeLlmResponse(llmResponse) {
		if (Array.isArray(llmResponse)) {
			return llmResponse.join("\n");
		}
		if (typeof llmResponse === "string") {
			return llmResponse;
		}
		throw new Error("Unexpected LLM response type");
	}

	// Extracts the CSV code block from the LLM response
	function extractCsvFromMarkdown(text) {
		const match = text.match(/```csv\s*([\s\S]*?)\s*```/i);
		return match ? match[1].trim() : null;
	}

	// Separates each CSV line
	function parseCsvLine(line) {
		const result = [];
		let current = "";
		let inQuotes = false;

		for (let i = 0; i < line.length; i++) {
			const char = line[i];
			const next = line[i + 1];

			if (char === '"' && inQuotes && next === '"') {
				current += '"';
				i++;
			} else if (char === '"') {
				inQuotes = !inQuotes;
			} else if (char === "," && !inQuotes) {
				result.push(current);
				current = "";
			} else {
				current += char;
			}
		}

		result.push(current);
		return result;
	}

	// Ensures any CSV escape characters are appropriately handled
	function escapeCsvField(value) {
		if (value == null) return "";
		if (/[",\n]/.test(value)) {
			return `"${value.replace(/"/g, '""')}"`;
		}
		return value;
	}

	function serializeCsv(rows) {
		return rows
			.map(row => row.map(escapeCsvField).join(","))
			.join("\n");
	}

	// Fixes two known issues:
	//		Missing column for non-scaleQuestions
	//		Extra column for scaleQuestions
	function fixMissingColumn(csvText, missingColumnIndex, extraColumnIndex) {
		const lines = csvText
			.split(/\r?\n/)
			.map(l => l.trim())
			.filter(Boolean);

		if (!lines.length) throw new Error("CSV is empty");

		const rows = lines.map(parseCsvLine);
		const header = rows[0];
		const expectedCols = header.length;

		const fixedRows = rows.map((row, i) => {
			// Header stays untouched
			if (i === 0) return row;

			// Row is correct
			if (row.length === expectedCols) return row;
			
			// Columns are added or removed based on the difference
			//	between the actual and expected columns.
			if (row.length != expectedCols) {
				const diff = expectedCols - row.length;
				if (expectedCols > row.length){
					const fixed = row.slice();
					for (i = 0; i < Math.abs(diff); i++){
						fixed.splice(missingColumnIndex, 0, "");
					}
					return fixed;
				}
				if (expectedCols < row.length){
					const fixed = row.slice();
					for (i = 0; i < Math.abs(diff); i++) {
						fixed.splice(extraColumnIndex, 1);
					}
					return fixed;
				}
			}

			// Anything else is unsafe
			throw new Error(
			`Row ${i + 1} malformed: ${row.length} columns (expected ${expectedCols})`
			);
		});

		return serializeCsv(fixedRows);
	}


	// Downloads a CSV file of the last LLM response
	async function onDownloadCSV() {
		setIsDownloading(true);
		setError("");
		// Extracting the CSV code block from the last LLM response and 
		// 	converting it to a CSV file. The CSV file is automatically 
		// 	downloaded after generation
		const normalizedText = normalizeLlmResponse(lastResponse);
		const rawCsv = extractCsvFromMarkdown(normalizedText);
		if (!rawCsv) {
				alert("No CSV found in the response");
				setIsDownloading(false);
				return
			}
		try {
			// Fixing two known issues - missing or extra
			//	columns
			const fixedCsv = fixMissingColumn(rawCsv, 7, 4);
			// Downloading the CSV
			const blob = new Blob(["\ufeff" + fixedCsv], { type: 'text/csv;charset=utf-8;' });
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

		{/*This button is for submitting the user message.*/}
		<form onSubmit={onSend} className="row">
			<input
				className="input"
				value={input}
				placeholder='Examples: "Help me with questions on {topic}" or "What makes a good survey question?".'
				onChange={(e) => setInput(e.target.value)}
				disabled={isLoading}
			/>
			<button className="button" type="submit" disabled={!canSend}>
				{isLoading ? <LoadingDots text = "Thinking" active = {isLoading} /> : "Send"}
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
				{isDownloading ? <LoadingDots text = "Getting CSV" active = {isDownloading} /> : "Download CSV"}
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