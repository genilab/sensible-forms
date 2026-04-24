/**
 * AuthComplete.jsx
 * 
 * Rendered when OAuth redirects back to "/" with ?oauth=complete.
 * Refreshes local auth, then closes the popup.
 */

import { useEffect } from "react";
import { useAuth } from "../services/authService.js";

export default function AuthComplete() {
  const { refresh } = useAuth();

  useEffect(() => {
    void refresh();

    const t = setTimeout(() => {
      try {
        window.close();
      } catch (err) {
        console.error("window close error", err);
      }
    }, 1000);

    return () => clearTimeout(t);
  }, [refresh]);

  return (
    <div style={{ padding: 20 }}>
      <h2>Authentication complete</h2>
      <p>This window will close automatically.</p>
    </div>
  );
}
