import { t } from "./strings";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly extra: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

function csrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)jq_csrf=([^;]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

async function ensureCsrf(): Promise<string | null> {
  // Le cookie CSRF est posé par le serveur à la première requête.
  if (!csrfToken()) await fetch("/api/health", { credentials: "same-origin" });
  return csrfToken();
}

function parseError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const { code, message, ...extra } = detail as Record<string, unknown>;
    return new ApiError(status, String(code ?? "error"), String(message ?? t("error.generic")), extra);
  }
  if (Array.isArray(detail)) {
    // Erreur de validation FastAPI.
    return new ApiError(status, "validation", t("error.validation"));
  }
  return new ApiError(status, "error", t("error.generic"));
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    const token = await ensureCsrf();
    if (token) headers["X-CSRF-Token"] = token;
  }
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network", t("error.network"));
  }

  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) throw parseError(response.status, data);
  return data as T;
}

export const api = {
  get: <T>(url: string) => request<T>("GET", url),
  post: <T>(url: string, body?: unknown) => request<T>("POST", url, body ?? {}),
  patch: <T>(url: string, body: unknown) => request<T>("PATCH", url, body),
  delete: <T>(url: string) => request<T>("DELETE", url),
};

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : t("error.generic");
}
