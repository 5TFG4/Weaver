/**
 * useFills Hook Tests
 */

import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFills } from "../../../src/hooks/useFills";
import { mockFills } from "../../mocks/handlers";
import type { ReactNode } from "react";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useFills", () => {
  it("returns fills for a run", async () => {
    const { result } = renderHook(() => useFills("run-2"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(mockFills.length);
    expect(result.current.data?.items[0].symbol).toBe("ETH/USD");
  });

  it("remains idle when runId is empty string", () => {
    const { result } = renderHook(() => useFills(""), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });

  it("remains idle when disabled", () => {
    const { result } = renderHook(() => useFills("run-2", { enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });
});
