/**
 * useAccount Hook Tests
 */

import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAccount, usePositions } from "../../../src/hooks/useAccount";
import { mockAccount, mockPositions } from "../../mocks/handlers";
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

describe("useAccount", () => {
  it("returns account data after fetch", async () => {
    const { result } = renderHook(() => useAccount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.account_id).toBe(mockAccount.account_id);
    expect(result.current.data?.portfolio_value).toBe("75000.00");
  });

  it("remains idle when disabled", () => {
    const { result } = renderHook(() => useAccount({ enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("usePositions", () => {
  it("returns positions data after fetch", async () => {
    const { result } = renderHook(() => usePositions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(mockPositions.length);
    expect(result.current.data?.items[0].symbol).toBe("ETH/USD");
  });

  it("remains idle when disabled", () => {
    const { result } = renderHook(() => usePositions({ enabled: false }), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });
});
