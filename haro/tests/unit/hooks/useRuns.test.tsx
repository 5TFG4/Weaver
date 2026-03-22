import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useRuns,
  useRun,
  useCreateRun,
  useStartRun,
  useStopRun,
} from "../../../src/hooks/useRuns";
import { mockRuns } from "../../mocks/handlers";
import type { ReactNode } from "react";

// Wrapper with QueryClient for testing hooks
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useRuns", () => {
  it("returns loading state initially", () => {
    const { result } = renderHook(() => useRuns(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns data after fetch completes", async () => {
    const { result } = renderHook(() => useRuns(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.items).toHaveLength(mockRuns.length);
    expect(result.current.data?.items[0].id).toBe("run-1");
  });
});

describe("useRun", () => {
  it("fetches a single run by ID", async () => {
    const { result } = renderHook(() => useRun("run-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.id).toBe("run-1");
    expect(result.current.data?.strategy_id).toBe("sma-crossover");
  });

  it("does not fetch when id is empty", () => {
    const { result } = renderHook(() => useRun(""), {
      wrapper: createWrapper(),
    });

    // enabled: Boolean('') === false, so query should not be fetching
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useCreateRun", () => {
  it("creates a run and invalidates list cache", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useCreateRun(), { wrapper });

    result.current.mutate({
      strategy_id: "test-strategy",
      mode: "backtest",
      symbols: ["BTC/USD"],
      timeframe: "1h",
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.strategy_id).toBe("test-strategy");
    expect(result.current.data?.status).toBe("pending");
    expect(invalidateSpy).toHaveBeenCalled();
  });
});

describe("useStartRun", () => {
  it("starts a run and updates cache", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const setQueryDataSpy = vi.spyOn(queryClient, "setQueryData");

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useStartRun(), { wrapper });

    result.current.mutate("run-1");

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.status).toBe("running");
    expect(result.current.data?.started_at).toBeDefined();
    expect(setQueryDataSpy).toHaveBeenCalled();
    expect(invalidateSpy).toHaveBeenCalled();
  });
});

describe("useStopRun", () => {
  it("stops a run and updates cache", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const setQueryDataSpy = vi.spyOn(queryClient, "setQueryData");

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useStopRun(), { wrapper });

    result.current.mutate("run-1");

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.status).toBe("stopped");
    expect(result.current.data?.stopped_at).toBeDefined();
    expect(setQueryDataSpy).toHaveBeenCalled();
    expect(invalidateSpy).toHaveBeenCalled();
  });
});
