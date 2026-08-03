import axios, { AxiosError } from "axios";

export type JsonRecord = Record<string, unknown>;

export class CloudwaysApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "CloudwaysApiError";
  }
}

export function getEnv(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (!value) {
    throw new CloudwaysApiError(`Missing required environment variable: ${name}`);
  }
  return value;
}

export function optionalEnv(name: string, fallback?: string): string | undefined {
  return process.env[name] ?? fallback;
}

export function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

export function toArray<T = JsonRecord>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[];
  if (!value || typeof value !== "object") return [];

  const record = value as JsonRecord;
  for (const key of ["servers", "apps", "applications", "data", "items", "backups", "logs"]) {
    if (Array.isArray(record[key])) return record[key] as T[];
  }

  return [];
}

export function unwrapData<T = unknown>(value: unknown): T {
  if (value && typeof value === "object" && "data" in value) {
    return (value as JsonRecord).data as T;
  }
  return value as T;
}

export function firstString(record: JsonRecord, keys: string[], fallback = ""): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.length > 0) return value;
    if (typeof value === "number") return String(value);
  }
  return fallback;
}

export function firstNumber(record: JsonRecord, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number") return value;
    if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value))) {
      return Number(value);
    }
  }
  return undefined;
}

export function sanitizeEnvironmentVariables(value: unknown): JsonRecord[] {
  return toArray<JsonRecord>(value).map((item) => {
    const name = firstString(item, ["name", "variable_name", "key"]);
    return {
      name,
      value: item.value ? "[redacted]" : undefined,
      is_secret: Boolean(item.is_secret ?? item.secret ?? item.hidden),
    };
  });
}

export function jsonContent(data: unknown) {
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(data, null, 2),
      },
    ],
  };
}

export function toolError(error: unknown) {
  const message = formatError(error);
  return {
    isError: true,
    content: [
      {
        type: "text" as const,
        text: message,
      },
    ],
  };
}

export function formatError(error: unknown): string {
  if (error instanceof CloudwaysApiError) {
    return error.status ? `${error.message} (HTTP ${error.status})` : error.message;
  }

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status;
    const details = axiosError.response?.data;
    const message =
      typeof details === "object" && details && "message" in details
        ? String((details as JsonRecord).message)
        : axiosError.message;
    return status ? `${message} (HTTP ${status})` : message;
  }

  return error instanceof Error ? error.message : String(error);
}

