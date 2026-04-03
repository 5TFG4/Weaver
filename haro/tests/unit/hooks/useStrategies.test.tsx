import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useStrategies } from "../../../src/hooks/useStrategies";
import type { ReactNode } from "react";

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

describe("useStrategies", () => {
  it("fetches and returns strategies", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useStrategies(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(2);
    expect(result.current.data![0]).toHaveProperty("config_schema");
    expect(result.current.data![0].id).toBe("sample");
    expect(result.current.data![1].id).toBe("sma-crossover");
  });
});
