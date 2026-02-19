import { describe, it, expect } from "vitest";
import { fetchOrders, fetchOrder } from "../../../src/api/orders";
import { mockOrders } from "../../mocks/handlers";

describe("Orders API", () => {
  it("fetchOrders returns paginated list", async () => {
    const result = await fetchOrders();

    expect(result.items).toHaveLength(mockOrders.length);
    expect(result.total).toBe(mockOrders.length);
    expect(result.page).toBe(1);
  });

  it("fetchOrders filters by run_id", async () => {
    const result = await fetchOrders({ run_id: "run-1" });

    expect(result.items).toHaveLength(1);
    expect(result.items[0].run_id).toBe("run-1");
  });

  it("fetchOrder returns single order by id", async () => {
    const result = await fetchOrder("order-1");

    expect(result.id).toBe("order-1");
    expect(result.symbol).toBe("BTC/USD");
    expect(result.status).toBe("filled");
  });
});
