/**
 * questionGenerationService.js
 *
 * Responsible for API calls related to question generation.
 *
 * Responsibilities:
 * - Sending user input to backend
 * - Receiving AI-generated responses from backend
 * - Receiving generated survey questions from backend
 *
 * Prevents direct HTTP calls inside UI components.
 */

// Example Code:
import { postJson } from "./http.js";

/**
 * @param {string} topic
 * @returns {Promise<{questions: string[]}>}
 */
export async function generateQuestions(topic) {
  return await postJson("/question-generation/", { topic });
}
