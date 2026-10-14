import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { initBrainToken } from "./api.js";
import "./theme.css";

// F-20: fetch the local brain token first, then render (every changing call carries it)
initBrainToken().finally(() => createRoot(document.getElementById("root")).render(<App />));
