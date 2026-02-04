import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRuns } from "../../../src/hooks/useRuns";
import { mockRuns } from "../../mocks/handlers";

// Wrapper with QueryClient for testing hooks
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
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
