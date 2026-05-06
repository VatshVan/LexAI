import { useMemo } from "react";

export function useVerification(result: any) {
  return useMemo(() => {
    const report = result?.verification_report;
    return {
      report,
      verifiedCount: report?.total_claims_verified ?? 0,
      purgedCount: report?.total_claims_purged ?? 0,
      verificationScore: report?.verification_score ?? 0
    };
  }, [result]);
}
