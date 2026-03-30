import { FormattedValue } from "./types";

const PCT_KEYS = new Set([
  "dividendYield",
  "trailingAnnualDividendYield",
  "fiveYearAvgDividendYield",
  "payoutRatio",
  "profitMargins",
  "grossMargins",
  "operatingMargins",
  "ebitdaMargins",
  "returnOnEquity",
  "returnOnAssets",
  "revenueGrowth",
  "earningsGrowth",
  "earningsQuarterlyGrowth",
  "yearChange",
]);

const BIG_KEYS = new Set([
  "marketCap",
  "enterpriseValue",
  "ebitda",
  "totalCash",
  "totalDebt",
  "sharesOutstanding",
]);

const DATE_KEYS = new Set(["lastDividendDate", "exDividendDate"]);

export function formatValue(key: string, val: unknown): FormattedValue {
  if (val === null || val === undefined) {
    return { text: "—", cls: "null" };
  }

  if (PCT_KEYS.has(key) && typeof val === "number") {
    const pct = val * 100;
    const cls = pct > 0 ? "positive" : pct < 0 ? "negative" : "";
    const prefix = pct > 0 ? "+" : "";
    return { text: prefix + pct.toFixed(2) + "%", cls };
  }

  if (BIG_KEYS.has(key) && typeof val === "number") {
    return { text: formatLargeNumber(val) };
  }

  if (DATE_KEYS.has(key) && typeof val === "number") {
    return { text: new Date(val * 1000).toLocaleDateString() };
  }

  if (typeof val === "number") {
    return {
      text: Number.isInteger(val) ? val.toLocaleString() : val.toFixed(4),
    };
  }

  return { text: String(val) };
}

export function formatLargeNumber(n: number): string {
  if (Math.abs(n) >= 1e12) return (n / 1e12).toFixed(2) + "T";
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + "M";
  return n.toLocaleString();
}

export function toLabel(key: string): string {
  return key
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, (s) => s.toUpperCase());
}

export const TABLE_LABELS: Record<string, string> = {
  fast_info: "Fast Info",
  analyst_consensus: "Analyst Consensus",
  balance_sheet: "Balance Sheet",
  company_profile: "Company Profile",
  dividends: "Dividends",
  growth: "Growth",
  profitability: "Profitability",
  valuation: "Valuation",
};
