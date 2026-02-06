/**
 * StatusBadge Component
 *
 * Reusable pill-shaped badge for displaying run status and mode.
 * Color-coded for quick visual identification.
 */

export type BadgeVariant =
  | "running"
  | "completed"
  | "stopped"
  | "pending"
  | "error"
  | "live"
  | "paper"
  | "backtest";

const variantStyles: Record<BadgeVariant, string> = {
  running: "bg-green-500/20 text-green-400",
  completed: "bg-blue-500/20 text-blue-400",
  stopped: "bg-yellow-500/20 text-yellow-400",
  pending: "bg-slate-500/20 text-slate-400",
  error: "bg-red-500/20 text-red-400",
  live: "bg-red-500/20 text-red-400",
  paper: "bg-purple-500/20 text-purple-400",
  backtest: "bg-cyan-500/20 text-cyan-400",
};

export interface StatusBadgeProps {
  variant: BadgeVariant;
  label?: string;
}

export function StatusBadge({ variant, label }: StatusBadgeProps) {
  const displayText = label ?? variant;
  const style = variantStyles[variant] ?? variantStyles.pending;

  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${style}`}
    >
      {displayText}
    </span>
  );
}
