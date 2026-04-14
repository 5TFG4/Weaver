/**
 * AccountCard Component Tests
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AccountCard } from "../../../../src/components/runs/AccountCard";
import { mockAccount } from "../../../mocks/handlers";

describe("AccountCard", () => {
  it("renders account fields when data is provided", () => {
    render(<AccountCard account={mockAccount} isLoading={false} />);

    expect(screen.getByTestId("account-card")).toBeInTheDocument();
    expect(screen.getByText("$75,000.00")).toBeInTheDocument();
    expect(screen.getByText("$50,000.00")).toBeInTheDocument();
    expect(screen.getByText("$25,000.00")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  it("renders loading skeleton when isLoading", () => {
    render(<AccountCard account={null} isLoading={true} />);

    expect(screen.getByTestId("account-card-loading")).toBeInTheDocument();
  });

  it("renders nothing when account is null and not loading", () => {
    const { container } = render(
      <AccountCard account={null} isLoading={false} />,
    );

    expect(container.firstChild).toBeNull();
  });
});
