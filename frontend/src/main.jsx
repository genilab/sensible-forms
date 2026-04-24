/**
 * main.jsx
 *
 * Boots the example React app.
 */

import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App.jsx";
import AuthComplete from "./pages/AuthComplete.jsx";
import "./styles.css";

// Route authentication return location
const params = new URLSearchParams(location.search);
const isOauthCallback = params.get("oauth") === "complete";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {isOauthCallback ? <AuthComplete /> : <App />}
  </React.StrictMode>
);
