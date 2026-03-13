/**
 * analysisAssistantService.js
 *
 * Encapsulates API calls related to the Analysis Assistant domain.
 *
 * Responsibilities:
 * - Sending analysis requests to backend
 * - Returning structured analysis responses
 *
 * This layer isolates HTTP logic from UI components.
 */

// Example Code:
import { postJson, postMultipart } from "./http.js";

/**
 * @param {string} data_summary
 * @param {string | undefined} session_id
 * @returns {Promise<{insights: string, session_id: string}>}
 */
export async function analyzeData(data_summary, session_id) {
	return await postJson("/analysis/", { data_summary, session_id });
}

/**
 * Upload a CSV to the Analysis Assistant ingestion pipeline.
 * Backend: POST /analysis/upload (multipart form field: "file")
 *
 * @param {File} file
 * @param {string | undefined} session_id
 * @returns {Promise<{insights: string, session_id: string}>}
 */
export async function uploadAnalysisCsv(file, session_id) {
	const formData = new FormData();
	formData.append("file", file);
	if (session_id) formData.append("session_id", session_id);
	return await postMultipart("/analysis/upload", formData);
}
