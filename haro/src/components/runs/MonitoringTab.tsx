/**
 * MonitoringTab Component
 *
 * Composition component for the run monitoring view.
 * Shows live account/position snapshots for running runs,
 * and fill history for all live/paper runs.
 */

import { useAccount, usePositions } from "../../hooks/useAccount";
import { useFills } from "../../hooks/useFills";
import { AccountCard } from "./AccountCard";
import { PositionsTable } from "./PositionsTable";
import { RunFillsTable } from "./RunFillsTable";

export interface MonitoringTabProps {
  runId: string;
  isRunning: boolean;
}

export function MonitoringTab({ runId, isRunning }: MonitoringTabProps) {
  const showLiveSnapshot = isRunning;

  const accountQuery = useAccount({ enabled: showLiveSnapshot });
  const positionsQuery = usePositions({
    enabled: showLiveSnapshot,
    refetchInterval: showLiveSnapshot ? 5_000 : false,
  });
  const fillsQuery = useFills(runId, { enabled: true });

  return (
    <div data-testid="monitoring-tab" className="space-y-6">
      {/* Live snapshots: only for running runs */}
      {showLiveSnapshot && accountQuery.isError && (
        <div
          data-testid="monitoring-snapshot-error"
          className="bg-red-900/20 border border-red-700 rounded-lg p-4"
        >
          <p className="text-red-400 text-sm">
            Unable to load account snapshot.
          </p>
        </div>
      )}

      {showLiveSnapshot && !accountQuery.isError && (
        <AccountCard
          account={accountQuery.data ?? null}
          isLoading={accountQuery.isLoading}
        />
      )}

      {showLiveSnapshot && positionsQuery.isError ? (
        <div
          data-testid="positions-error"
          className="bg-red-900/20 border border-red-700 rounded-lg p-4"
        >
          <p className="text-red-400 text-sm">Unable to load positions.</p>
        </div>
      ) : showLiveSnapshot ? (
        <PositionsTable positions={positionsQuery.data?.items ?? []} />
      ) : (
        <div
          data-testid="monitoring-history-note"
          className="bg-slate-800 border border-slate-700 rounded-lg p-4"
        >
          <p className="text-slate-400 text-sm">
            Account and position snapshots are only shown while the run is
            active. Historical fills remain available below.
          </p>
        </div>
      )}

      {/* Fills: always shown for live/paper runs */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-3">Fills</h3>
        <RunFillsTable
          fills={fillsQuery.data?.items ?? []}
          isLoading={fillsQuery.isLoading}
          isError={fillsQuery.isError}
        />
      </div>
    </div>
  );
}
