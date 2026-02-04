import { describe, it, expect } from "vitest";
import { fetchRuns, fetchRun, createRun, stopRun } from "../../../src/api/runs";
import { mockRuns } from "../../mocks/handlers";

describe("Runs API", () => {
  it("fetchRuns returns paginated list", async () => {
    const result = await fetchRuns();

    expect(result.items).toHaveLength(mockRuns.length);
    expect(result.total).toBe(mockRuns.length);
    expect(result.page).toBe(1);
    expect(result.items[0].id).toBe("run-1");
  });

  it("fetchRun returns single run by id", async () => {
    const result = await fetchRun("run-1");

    expect(result.id).toBe("run-1");
    expect(result.strategy_id).toBe("sma-crossover");
    expect(result.mode).toBe("backtest");
  });

  it("createRun posts correct payload", async () => {
    const newRun = await createRun({
      strategy_id: "test-strategy",
      mode: "paper",
      symbols: ["BTC/USD"],
      timeframe: "1h",
    });

    expect(newRun.strategy_id).toBe("test-strategy");
    expect(newRun.mode).toBe("paper");
    expect(newRun.symbols).toEqual(["BTC/USD"]);
    expect(newRun.status).toBe("pending");
  });

  it("stopRun posts to correct endpoint", async () => {
    const result = await stopRun("run-2");

    expect(result.status).toBe("stopped");
    expect(result.stopped_at).toBeDefined();
  });
});
