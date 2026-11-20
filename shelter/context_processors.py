def csp_nonce(request):
    """The per-request nonce for inline <script> tags: <script nonce="{{ csp_nonce }}">."""
    return {"csp_nonce": getattr(request, "csp_nonce", "")}
