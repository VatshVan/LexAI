import { Badge } from "../ui/Badge";

export function VerificationBadge({
  verdict
}: {
  verdict: "VERIFIED" | "INSUFFICIENT" | "PURGED" | string;
}) {
  const variant =
    verdict === "VERIFIED"
      ? "verified"
      : verdict === "INSUFFICIENT"
      ? "insufficient"
      : verdict === "PURGED"
      ? "purged"
      : "default";
  return <Badge label={verdict} variant={variant} />;
}
