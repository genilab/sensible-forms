/**
 * session.js
 *
 * Tiny helper for generating/persisting a UUID session id in the browser.
 * Used to keep backend LangGraph checkpoint threads stable per chat session.
 */

function fallbackUuidV4() {
	// RFC4122-ish UUIDv4 using Web Crypto when available.
	const bytes = new Uint8Array(16);
	crypto.getRandomValues(bytes);
	bytes[6] = (bytes[6] & 0x0f) | 0x40;
	bytes[8] = (bytes[8] & 0x3f) | 0x80;
	const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0"));
	return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex
		.slice(6, 8)
		.join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10, 16).join("")}`;
}

/**
 * @param {string} storageKey
 * @returns {string} UUID
 */
export function getOrCreateSessionId(storageKey) {
	const existing = localStorage.getItem(storageKey);
	if (existing) return existing;

	const id = typeof crypto?.randomUUID === "function" ? crypto.randomUUID() : fallbackUuidV4();
	localStorage.setItem(storageKey, id);
	return id;
}
