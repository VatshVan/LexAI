import { VerificationBadge } from "./VerificationBadge";

export function ClaimCard({
  claim,
  variant
}: {
  claim: any;
  variant: "VERIFIED" | "INSUFFICIENT";
}) {
  return (
    <div
      className={`p-4 rounded-lg border-l-4 bg-surface-800 border-surface-600 ${
        variant === "VERIFIED" ? "border-l-verified" : "border-l-flagged"
      }`}
    >
      <p className="text-sm text-gray-200">{claim.claim_text}</p>
      <div className="flex items-center gap-2 mt-2">
        <VerificationBadge verdict={variant} />
        {claim.verification_score && (
          <span className="text-xs text-gray-500 font-mono">
            score: {(claim.verification_score * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
}
