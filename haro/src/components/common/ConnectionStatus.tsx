/**
 * Connection Status Indicator
 *
 * M7-6: SSE Integration
 * Displays the SSE connection status with a colored dot.
 */

interface ConnectionStatusProps {
  isConnected: boolean;
}

export function ConnectionStatus({ isConnected }: ConnectionStatusProps) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span
        data-testid="connection-dot"
        className={`inline-block w-2 h-2 rounded-full ${
          isConnected ? "bg-green-400" : "bg-red-400"
        }`}
      />
      <span className={isConnected ? "text-green-400" : "text-red-400"}>
        {isConnected ? "Connected" : "Disconnected"}
      </span>
    </div>
  );
}
