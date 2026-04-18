/**
 * formDeploymentService.js
 *
 * Handles API communication for form deployment.
 *
 * Responsibilities:
 * - Sending form deployment requests to backend
 * - Returning deployment status or results
 *
 * Keeps networking concerns separate from UI logic.
 */

// Example Code:
import { postJson, postMultipart, getJson } from "./http.js";

/**
 * @param {string} message
 * @param {string | undefined} session_id
 * @param {{ last_deploy_filename?: (string|null), last_deploy_status?: (string|null), last_deploy_feedback?: (string|null) } | undefined} context
 * @returns {Promise<{message: string, session_id: string}>}
 */
export async function sendDeploymentMessage(message, session_id, context) {
	return await postJson("/form-deployment/chat", {
		message,
		session_id,
		last_deploy_filename: context?.last_deploy_filename ?? null,
		last_deploy_status: context?.last_deploy_status ?? null,
		last_deploy_feedback: context?.last_deploy_feedback ?? null
	});
}

/**
 * @param {File} file
 * @returns {Promise<{filename: string, status: string, feedback: string}>}
 */
export async function deploySurveyCsv(file) {
	const formData = new FormData();
	formData.append("file", file);
	return await postMultipart("/form-deployment/deploy", formData);
}

/**
 * @param {string} formId
 * @returns {Promise<{content: string}>}
 */
export async function getFormResponses(formId) {
	return await getJson(`/form-deployment/retrieve?formId=${formId}`);
}
