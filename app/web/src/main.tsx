import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./theme.css";

const rootElMaybe = document.getElementById("root");

if (!rootElMaybe) {
  throw new Error("Missing #root element");
}

const rootEl: HTMLElement = rootElMaybe;

function showFatalError(message: string) {
  rootEl.innerHTML = "";
  const pre = document.createElement("pre");
  pre.style.whiteSpace = "pre-wrap";
  pre.style.wordBreak = "break-word";
  pre.style.padding = "16px";
  pre.style.margin = "16px";
  pre.style.borderRadius = "6px";
  pre.style.border = "1px solid rgba(192, 198, 204, 0.25)";
  pre.style.background = "rgba(17, 17, 17, 0.85)";
  pre.style.color = "rgba(255, 180, 166, 0.95)";
  pre.style.fontFamily =
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace';
  pre.textContent = `Stock Viewer failed to start\n\n${message}`;
  rootEl.appendChild(pre);
}

window.addEventListener("error", (event) => {
  const err = event.error;
  const details =
    err instanceof Error
      ? `${err.name}: ${err.message}\n${err.stack ?? ""}`
      : String(event.message);
  showFatalError(details);
});

window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason;
  const details =
    reason instanceof Error
      ? `${reason.name}: ${reason.message}\n${reason.stack ?? ""}`
      : String(reason);
  showFatalError(details);
});

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  override componentDidCatch(error: Error) {
    showFatalError(`${error.name}: ${error.message}\n${error.stack ?? ""}`);
  }

  override render() {
    if (this.state.error) {
      return null;
    }
    return this.props.children;
  }
}

try {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>,
  );
} catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  showFatalError(message);
  throw err;
}
