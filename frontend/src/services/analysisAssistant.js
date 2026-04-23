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

import { postJson, postMultipart } from "./http.js";

/**
 * Upload a survey responses CSV. 
 * @param {File} file
 * @returns {Promise<{filename: string, file_id: string}>}
 */
export async function uploadSurveyCsv(file) {
	const form = new FormData();
	form.append("file", file);
	return await postMultipart("/uploads/", form);
}

/**
 * Chat with the analysis assistant about an uploaded dataset.
 * @param {{message: string, session_id?: string, upload_mode?: boolean, file_id?: string}} payload
 * @returns {Promise<{message: string, session_id: string, active_file_id?: string, dataset_profile?: any}>}
 */
export async function chatAnalysis(payload) {
	return await postJson("/analysis/chat", payload);
}
