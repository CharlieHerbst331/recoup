"""Safe adapter failures consumed by the bounded loop; design/02 §5.2, §5.9."""


class ProviderUnavailable(Exception):
    """A provider failure that must stop the run without automatic retries."""


class InvalidResponse(ValueError):
    """An unusable completion; no tool work may be inferred from it."""
