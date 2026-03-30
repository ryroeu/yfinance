import { useState, useRef } from "react";
import { StockResponse, StockData } from "./types";
import { formatValue, toLabel, TABLE_LABELS } from "./utils";

export default function App() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stock, setStock] = useState<StockResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function search() {
    const symbol = input.trim().toUpperCase();
    if (!symbol) return;

    setLoading(true);
    setError(null);
    setStock(null);

    try {
      const res = await fetch(`/api/stock/${encodeURIComponent(symbol)}`);
      const json: StockResponse = await res.json();
      setStock(json);
    } catch {
      setError("Failed to fetch data. Is the server running?");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") search();
  }

  const companyName =
    stock?.tables.company_profile?.data?.["longName"] as string | undefined;

  return (
    <>
      <nav className="topnav">
        <div className="nav-inner">
          <div className="nav-brand">
            <span className="y-badge">Y!</span>
            <span className="nav-product">Finance</span>
          </div>
        </div>
      </nav>

      <main>
        <header>
          <h1>Stock Data Viewer</h1>
          <p>Powered by Yahoo Finance data</p>
        </header>

        <div className="search-bar">
          <div className="search-wrap">
            <svg
              className="search-icon"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              placeholder="Search symbol (e.g. AAPL, MSFT)"
              autoComplete="off"
              value={input}
              onChange={(e) => setInput(e.target.value.toUpperCase())}
              onKeyDown={handleKeyDown}
            />
          </div>
          <button onClick={search} disabled={loading}>
            Search
          </button>
        </div>

        <div className="status-row">
          {loading && <div className="spinner" />}
          {error && <span className="status-error">{error}</span>}
        </div>

        {stock && (
          <div className="results">
            <div className="symbol-header">
              <div className="ticker">{stock.symbol}</div>
              {companyName && (
                <div className="company-name">{companyName}</div>
              )}
            </div>
            <div className="grid">
              {Object.entries(stock.tables).map(([tableKey, tableData]) => (
                <StockCard key={tableKey} tableKey={tableKey} data={tableData} />
              ))}
            </div>
          </div>
        )}
      </main>

      <footer>
        <p>Data provided by Yahoo Finance &middot; For informational purposes only</p>
      </footer>
    </>
  );
}

function StockCard({
  tableKey,
  data,
}: {
  tableKey: string;
  data: StockData;
}) {
  const isError = data.status === "error";

  return (
    <div className={`card${isError ? " error" : ""}`}>
      <div className="card-title">
        {TABLE_LABELS[tableKey] ?? tableKey}
      </div>
      <div className="card-body">
        {isError ? (
          <span>{data.error}</span>
        ) : (
          data.data &&
          Object.entries(data.data).map(([key, val]) => {
            if (key === "symbol") return null;
            const { text, cls } = formatValue(key, val);
            return (
              <div className="row" key={key}>
                <span className="label">{toLabel(key)}</span>
                <span className={`value${cls ? ` ${cls}` : ""}`}>{text}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
