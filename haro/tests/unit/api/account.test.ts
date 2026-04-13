/**
 * Account API Tests
 */

import { describe, it, expect } from "vitest";
import { fetchAccount, fetchPositions } from "../../../src/api/account";
import { mockAccount, mockPositions } from "../../mocks/handlers";

describe("Account API", () => {
  it("fetchAccount returns account snapshot", async () => {
    const result = await fetchAccount();

    expect(result.account_id).toBe(mockAccount.account_id);
    expect(result.buying_power).toBe("50000.00");
    expect(result.portfolio_value).toBe("75000.00");
    expect(result.currency).toBe("USD");
    expect(result.status).toBe("ACTIVE");
  });

  it("fetchPositions returns open positions", async () => {
    const result = await fetchPositions();

    expect(result.items).toHaveLength(mockPositions.length);
    expect(result.total).toBe(mockPositions.length);
    expect(result.items[0].symbol).toBe("ETH/USD");
    expect(result.items[0].side).toBe("long");
    expect(result.items[0].unrealized_pnl).toBe("50.00");
  });
});
