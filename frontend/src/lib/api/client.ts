export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    fields?: Record<string, unknown>;
    retry_after?: number;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields?: Record<string, unknown>;
  /** Seconds to wait before trying again, when the server says so. */
  readonly retryAfter?: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.error.code;
    this.fields = body.error.fields;
    this.retryAfter = body.error.retry_after;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error?: unknown }).error === "object" &&
    (value as { error?: unknown }).error !== null
  );
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

const SAFE_METHODS = new Set(["GET", "HEAD"]);

type ApiFetchOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: Record<string, unknown>;
  signal?: AbortSignal;
};

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers = new Headers({ Accept: "application/json" });

  // Backend messages follow the language of the page, not the browser's.
  if (typeof document !== "undefined" && document.documentElement.lang) {
    headers.set("Accept-Language", document.documentElement.lang);
  }

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  if (!SAFE_METHODS.has(method)) {
    const csrfToken = readCookie("csrftoken");
    if (csrfToken) headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    if (isApiErrorBody(data)) {
      throw new ApiError(response.status, data);
    }
    throw new ApiError(response.status, {
      error: { code: "unknown_error", message: "Unexpected error." },
    });
  }

  return data as T;
}

/** A file from the API, such as a PDF. Errors still arrive as the JSON envelope. */
export async function apiDownload(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const response = await fetch(`/api${path}`, { credentials: "same-origin" });

  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      isApiErrorBody(data)
        ? data
        : { error: { code: "unknown_error", message: "Unexpected error." } },
    );
  }

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? null;
  return { blob: await response.blob(), filename };
}

/** Hands a downloaded file to the browser to save. */
export function saveFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
