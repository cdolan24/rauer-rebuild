from __future__ import annotations

import json
from collections.abc import Iterator

import httpx


class ApiClientError(Exception):
    """Raised when the backend API is unreachable or returns an error."""


class ApiAuthError(ApiClientError):
    """Raised when the backend rejects a request for bad/missing credentials."""


class ApiClient:
    """Thin HTTP client the Gradio frontend uses to talk to the FastAPI backend."""

    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = httpx.request(
                method, f"{self._base_url}{path}", timeout=self._timeout, **kwargs
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ApiClientError(f"Request to {path} failed: {e}") from e
        return response.json()

    def send_chat_stream(self, message: str, conversation_id: str) -> Iterator[dict]:
        """Stream chat events (`token`/`done`/`error`) from `/api/chat/stream`."""
        try:
            with httpx.stream(
                "POST",
                f"{self._base_url}/api/chat/stream",
                json={"message": message, "conversation_id": conversation_id},
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    yield json.loads(line[len("data: ") :])
        except httpx.HTTPError as e:
            raise ApiClientError(f"Request to /api/chat/stream failed: {e}") from e

    def list_documents(self) -> list[dict]:
        return self._request("GET", "/api/documents")["documents"]

    def get_document(self, document_id: str) -> dict:
        return self._request("GET", f"/api/documents/{document_id}")

    def upload_document(self, filename: str, content: bytes, admin_password: str) -> dict:
        try:
            response = httpx.post(
                f"{self._base_url}/api/documents/upload",
                files={"file": (filename, content, "application/pdf")},
                data={"admin_password": admin_password},
                timeout=self._timeout,
            )
            if response.status_code == 401:
                raise ApiAuthError("Incorrect admin password")
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ApiClientError(f"Upload failed: {e}") from e
        return response.json()

    def run_admin_query(self, sql: str, admin_password: str) -> dict:
        try:
            response = httpx.post(
                f"{self._base_url}/api/admin/query",
                json={"admin_password": admin_password, "sql": sql},
                timeout=self._timeout,
            )
            if response.status_code == 401:
                raise ApiAuthError("Incorrect admin password")
            if response.status_code == 400:
                raise ApiClientError(response.json().get("detail", "Query failed"))
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ApiClientError(f"Query failed: {e}") from e
        return response.json()

    def health(self) -> dict:
        return self._request("GET", "/api/health")

    def verify_admin_password(self, admin_password: str) -> bool:
        try:
            response = httpx.post(
                f"{self._base_url}/api/auth/verify",
                json={"admin_password": admin_password},
                timeout=self._timeout,
            )
        except httpx.HTTPError as e:
            raise ApiClientError(f"Could not verify admin password: {e}") from e
        return response.status_code == 200


class ControllerClient:
    """Thin HTTP client for the local service-control daemon
    (deploy/controller.py) - a separate process/base_url from the backend."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def control(self, service: str, action: str, admin_password: str) -> dict:
        try:
            response = httpx.post(
                f"{self._base_url}/control/{service}/{action}",
                json={"admin_password": admin_password},
                timeout=self._timeout,
            )
            if response.status_code == 401:
                raise ApiAuthError("Incorrect admin password")
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ApiClientError(f"Service control failed: {e}") from e
        return response.json()

    def status(self, service: str, admin_password: str) -> dict:
        try:
            response = httpx.get(
                f"{self._base_url}/control/{service}/status",
                params={"admin_password": admin_password},
                timeout=self._timeout,
            )
            if response.status_code == 401:
                raise ApiAuthError("Incorrect admin password")
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ApiClientError(f"Could not fetch status: {e}") from e
        return response.json()
