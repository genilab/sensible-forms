/**
 * uploadsService.js
 *
 * Encapsulates API calls related to raw file uploads.
 */

import { postMultipart } from "./http.js";

/**
 * Upload a CSV file to the backend.
 * Backend: POST /uploads/ (multipart form field: "file")
 *
 * @param {File} file
 * @returns {Promise<{filename: string}>}
 */
export async function uploadCsv(file) {
	const formData = new FormData();
	formData.append("file", file);
	return await postMultipart("/uploads/", formData);
}
