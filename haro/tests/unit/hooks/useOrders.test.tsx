import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useOrders,
  useOrder,
  useCancelOrder,
} from "../../../src/hooks/useOrders";
import { mockOrders } from "../../mocks/handlers";
import type { ReactNode } from "react";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useOrders", () => {
  it("returns loading state initially", () => {
    const { result } = renderHook(() => useOrders(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns order list after fetch completes", async () => {
    const { result } = renderHook(() => useOrders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(mockOrders.length);
    expect(result.current.data?.items[0].id).toBe("order-1");
    expect(result.current.data?.items[0].symbol).toBe("BTC/USD");
  });

  it("supports filtering by run_id", async () => {
    const { result } = renderHook(
      () => useOrders({ run_id: "run-1" }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // MSW handler filters by run_id
    expect(result.current.data?.items.every((o) => o.run_id === "run-1")).toBe(
      true,
    );
  });
});

describe("useOrder", () => {
  it("fetches a single order by ID", async () => {
    const { result } = renderHook(() => useOrder("order-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.id).toBe("order-1");
    expect(result.current.data?.side).toBe("buy");
    expect(result.current.data?.status).toBe("filled");
  });

  it("does not fetch when id is empty", () => {
    const { result } = renderHook(() => useOrder(""), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useCancelOrder", () => {
  it("cancels an order and invalidates cache", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useCancelOrder(), { wrapper });

    result.current.mutate("order-2");

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should invalidate both detail and list caches
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
  });
});
