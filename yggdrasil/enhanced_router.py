"""Compatibility shim for historical enhanced router imports."""

from yggdrasil.router import YggdrasilAIRouter


class EnhancedYggdrasilRouter(YggdrasilAIRouter):
    """Backwards-compatible alias of the primary Yggdrasil router."""

    def route_call(self, *args, **kwargs):
        """Compatibility passthrough to the canonical router entrypoint."""
        return super().route_call(*args, **kwargs)
