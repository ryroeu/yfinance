export interface StockData {
  status: "ok" | "error";
  data?: Record<string, unknown>;
  error?: string;
}

export interface StockResponse {
  symbol: string;
  tables: Record<string, StockData>;
}

export interface FormattedValue {
  text: string;
  cls?: string;
}
