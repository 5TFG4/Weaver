/**
 * Fills API Tests
 */

import { describe, it, expect } from "vitest";
import { fetchFills } from "../../../src/api/fills";
import { mockFills } from "../../mocks/handlers";

describe("Fills API", () => {
  it("fetchFills returns run-scoped fill history", async () => {
    const result = await fetchFills("run-2");

    expect(result.items).toHaveLength(mockFills.length);
    expect(result.total).toBe(mockFills.length);
    expect(result.items[0].id).toBe("fill-1");
    expect(result.items[0].symbol).toBe("ETH/USD");
    expect(result.items[0].side).toBe("buy");
    expect(result.items[0].commission).toBe("1.00");
  });
});
