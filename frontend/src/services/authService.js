/**
 * authService.js
 * 
 * Handles API communication for authorization pathways
 */

import { useCallback, useEffect, useState } from "react";
import { getApiBaseUrl } from "./apiBase.js";
import { getJson } from "./http.js";

/**
 * Check /auth/status route to determine if the user is logged in
 * @returns {Promise<{isAuth: boolean}>}
 */
export async function getAuthStatus() {
    const token = localStorage.getItem("refresh_token");
    return { isAuth: !!token };
}

/**
 * Redirect to /auth/start route
 */
export function handleLogin() {
	//window.location.href = `${getApiBaseUrl()}/auth/start`;
    window.open(`${getApiBaseUrl()}/auth/start`, "_blank");
}

/**
 * Execute the logout backend function at /auth/logout
 */
export function handleLogout() {
  localStorage.removeItem("refresh_token");
}

// Track and handle async authorization processes
export function useAuth() {
    const [isAuth, setIsAuth] = useState(false);
    const [loading, setLoading] = useState(true);

    // Update isAuth when called
    const refresh = useCallback(async () => {
        setLoading(true);
        try {
            const res = await getAuthStatus();
            setIsAuth(Boolean(res?.isAuth));
        } catch (err) {
            console.error("refresh error", err);
            setIsAuth(false);
        } finally {
            setLoading(false);
        }
    }, []);

    // Execute refresh on mount
    useEffect(() => {
        void refresh();
    }, [refresh]);

    // Run handleLogin when called
    const login = useCallback(() => {
        handleLogin();
    }, []);

    // Run handleLogout when called
    const logout = useCallback(async () => {
        setLoading(true);
        try {
            await handleLogout();
            setIsAuth(false);
        } catch (err) {
            console.error("logout error", err);
        } finally {
            setLoading(false);
        }
    }, []);

    return { isAuth, loading, refresh, login, logout }; 
}
