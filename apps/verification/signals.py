from django.dispatch import receiver
from apps.orchestration.pipeline import pre_finalize_signal
from apps.verification.engine import VerificationEngine
from apps.compilation.assembler import AssemblerService


@receiver(pre_finalize_signal)
def run_verification(sender, query_id, session_id, result_payload, query_session, **kwargs):
    claims = getattr(result_payload, "claims", None)
    if not claims:
        return
    verified_claims, report = VerificationEngine().run(
        query_id=query_id,
        session_id=session_id,
        claims=claims,
    )
    # Write report to QuerySession
    query_session.verification_report = report.model_dump(mode="json")
    query_session.save(update_fields=["verification_report"])

    # Replace claims in payload with verified subset
    result_payload.claims = verified_claims

    # Trigger compilation
    AssemblerService().assemble(
        query_id=query_id,
        verified_claims=verified_claims,
        summaries=report.claim_summaries,
        result_payload=result_payload,
    )
