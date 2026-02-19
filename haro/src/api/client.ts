/**
 * API Client
 *
 * Base HTTP client with error handling.
 * Uses fetch API (native browser).
 */

import type { ApiError } from "./types";

const API_BASE = "/api/v1";

/**
 * Custom error class for API errors
 */
export class ApiClientError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Make a GET request
 */
export async function get<T>(
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  const response = await fetch(url.toString(), {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  return handleResponse<T>(response);
}

/**
 * Make a POST request
 */
export async function post<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  return handleResponse<T>(response);
}

/**
 * Make a DELETE request
 */
export async function del<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  });

  return handleResponse<T>(response);
}

/**
 * Handle response and errors
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    let details: unknown;

    try {
      const errorBody = (await response.json()) as ApiError;
      errorMessage = errorBody.detail || errorMessage;
      details = errorBody;
    } catch {
      // Response body is not JSON, use default message
    }

    throw new ApiClientError(errorMessage, response.status, details);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/**
 * API client object for convenient imports
 */
export const apiClient = {
  get,
  post,
  delete: del,
};
