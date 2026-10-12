import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/zcool-kuaile/latin-400.css";
import "@fontsource/zcool-kuaile/chinese-simplified-400.css";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js");
  });
}
