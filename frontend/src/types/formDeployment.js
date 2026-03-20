/**
 * formDeployment.js
 *
 * Defines shared request and response structures
 * for the Form Deployment domain.
 *
 * Should mirror backend schema definitions.
 */

// Example Code:

/** @typedef {{ message: string, session_id?: string, last_deploy_filename?: (string|null), last_deploy_status?: (string|null), last_deploy_feedback?: (string|null) }} FormDeploymentRequest */
/** @typedef {{ message: string, session_id: string }} FormDeploymentResponse */
/** @typedef {{ filename: string, status: string, feedback: string }} FormDeploymentDeployResponse */

export {};
