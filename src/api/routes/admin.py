from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import AdminQueryRequest, AdminQueryResponse
from src.utils.auth import check_admin_password

router = APIRouter(tags=["admin"])


@router.post("/admin/query", response_model=AdminQueryResponse)
def run_query(payload: AdminQueryRequest, request: Request) -> AdminQueryResponse:
    """Run arbitrary SQL against the application database. Gated behind the
    same admin password as PDF upload - this is deliberately unrestricted
    (no statement-type filtering): "direct database access" means direct
    access, with the admin password as the only trust boundary."""
    config = request.app.state.config
    check_admin_password(
        request.app.state.admin_rate_limiter,
        request.client.host,
        config.admin_password,
        payload.admin_password,
    )

    conn = sqlite3.connect(config.data_storage_path)
    try:
        cursor = conn.execute(payload.sql)
        if cursor.description is not None:
            columns = [col[0] for col in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]
            conn.commit()
            return AdminQueryResponse(columns=columns, rows=rows)
        conn.commit()
        return AdminQueryResponse(columns=[], rows=[], rows_affected=cursor.rowcount)
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {e}") from e
    finally:
        conn.close()
