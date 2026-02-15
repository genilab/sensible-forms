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
import { postJson } from "./http.js";

/**
 * @param {string} data_summary
 * @returns {Promise<{insights: string}>}
 */
export async function analyzeData(data_summary) {
	return await postJson("/analysis/", { data_summary });
}
