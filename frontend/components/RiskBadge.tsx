import type { RiskLevel } from "@/types/predict";
import { riskLabel } from "@/lib/format";

const STYLES: Record<RiskLevel, string> = {
  low: "border-safe/30 bg-safe-soft text-safe",
  medium: "border-warn/30 bg-warn-soft text-warn",
  high: "border-phish/30 bg-phish-soft text-phish",
};

type RiskBadgeProps = {
  riskLevel: RiskLevel;
};

export function RiskBadge({ riskLevel }: RiskBadgeProps) {
  return (
    <span className={`inline-flex items-center border px-2 py-0.5 text-xs font-semibold tracking-wide ${STYLES[riskLevel]}`}>
      {riskLabel(riskLevel)}
    </span>
  );
}
