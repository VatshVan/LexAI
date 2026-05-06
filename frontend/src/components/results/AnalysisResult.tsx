import { ClaimCard } from "./ClaimCard";

export function AnalysisResult({ result }: { result: any }) {
  const payload = result.result_payload;
  const report = result.verification_report;
  if (!payload) return null;

  const verified = payload.claims?.filter((claim: any) => claim.is_verified && !claim.is_flagged) ?? [];
  const insufficient = payload.claims?.filter((claim: any) => claim.is_flagged) ?? [];
  const externalVerified = report?.total_claims_externally_verified ?? 0;
  const unresolvedCount = report
    ? report.total_claims_received -
      report.total_claims_verified -
      report.total_claims_purged -
      externalVerified
    : insufficient.length;

  return (
    <div className="space-y-6">
      {report && (
        <div className="flex items-center gap-4 p-4 bg-surface-800 border border-surface-600 rounded-xl">
          <span className="text-2xl font-mono font-bold text-verified">
            {(report.verification_score * 100).toFixed(0)}%
          </span>
          <div className="flex gap-3 text-xs">
            <span className="text-verified">{report.total_claims_verified} verified</span>
            {externalVerified > 0 && (
              <span className="text-accent">{externalVerified} external</span>
            )}
            <span className="text-flagged">{unresolvedCount} insufficient</span>
            <span className="text-purged">{report.total_claims_purged} purged</span>
          </div>
          <p className="text-gray-500 text-xs ml-auto">{payload.narrative_summary}</p>
        </div>
      )}

      {verified.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-widest">
            Verified Findings
          </h3>
          {verified.map((claim: any) => (
            <ClaimCard key={claim.claim_id} claim={claim} variant="VERIFIED" />
          ))}
        </div>
      )}

      {insufficient.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-widest">
            Flagged - Verify Manually
          </h3>
          {insufficient.map((claim: any) => (
            <ClaimCard key={claim.claim_id} claim={claim} variant="INSUFFICIENT" />
          ))}
        </div>
      )}
    </div>
  );
}
