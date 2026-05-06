"""
LexAI — Standardized API Response Envelope

Every API response uses this format:
{
    "success": bool,
    "data": any,
    "error": str | dict | null,
    "meta": {}
}
"""
from rest_framework.response import Response
from rest_framework import status as http_status


def api_response(
    data=None,
    error=None,
    meta=None,
    status_code=http_status.HTTP_200_OK,
    success=None,
):
    """
    Build a standardized API response.

    Args:
        data: Response payload (any serializable value)
        error: Error message or dict (null on success)
        meta: Additional metadata (pagination, timing, etc.)
        status_code: HTTP status code
        success: Explicit success flag. Auto-determined from status_code if None.
    """
    if success is None:
        success = 200 <= status_code < 400

    envelope = {
        "success": success,
        "data": data,
        "error": error,
        "meta": meta or {},
    }

    return Response(envelope, status=status_code)
