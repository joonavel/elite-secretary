from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from azure.identity import ClientSecretCredential

from src.domain.errors import ErrorCode, PipelineError


class GraphClient:
    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def request_bytes(self, path: str, *, params: dict[str, Any] | None = None) -> bytes:
        raise NotImplementedError


@dataclass(slots=True)
class AzureIdentityGraphClient(GraphClient):
    tenant_id: str
    client_id: str
    client_secret: str
    scope: str = "https://graph.microsoft.com/.default"
    base_url: str = "https://graph.microsoft.com/v1.0"
    timeout_seconds: float = 30.0
    _credential: ClientSecretCredential = field(init=False)

    def __post_init__(self) -> None:
        self._credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

    def _get_access_token(self) -> str:
        try:
            token = self._credential.get_token(self.scope)
            return token.token
        except Exception as error:
            raise PipelineError(
                code=ErrorCode.GRAPH_AUTH_FAILED,
                message=f"T-020 Graph auth failed: {error}",
                recoverable=False,
                step="T-020_GRAPH_AUTH",
            ) from error

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        bearer_token = self._get_access_token()
        if path.startswith("http://") or path.startswith("https://"):
            request_url = path
        else:
            request_url = path if path.startswith("/") else f"/{path}"
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.request(
                    method=method.upper(),
                    url=request_url,
                    headers={"Authorization": f"Bearer {bearer_token}"},
                    json=payload,
                    params=params,
                )
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as error:
            body = error.response.text[:300]
            raise PipelineError(
                code=ErrorCode.GRAPH_REQUEST_FAILED,
                message=f"T-020 Graph request failed: {error.response.status_code} {body}",
                recoverable=error.response.status_code >= 500,
                step="T-020_GRAPH_REQUEST",
            ) from error
        except httpx.HTTPError as error:
            raise PipelineError(
                code=ErrorCode.GRAPH_REQUEST_FAILED,
                message=f"T-020 Graph transport failed: {error}",
                recoverable=True,
                step="T-020_GRAPH_REQUEST",
            ) from error

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request_raw(method, path, payload=payload, params=params)
        return response.json()

    def request_bytes(self, path: str, *, params: dict[str, Any] | None = None) -> bytes:
        response = self._request_raw("GET", path, params=params)
        return response.content
