from __future__ import annotations


class GraphClient:
    """Interface placeholder for T-020/T-027 integrations."""

    def request(self, method: str, path: str, *, payload: dict | None = None) -> dict:
        raise NotImplementedError
