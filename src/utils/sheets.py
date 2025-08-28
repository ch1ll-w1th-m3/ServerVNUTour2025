"""
Google Sheets fetching utilities
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple

import aiohttp


HEADER_MAP = {
    "STT": "stt",
    "Tên đội": "team_name",
    "ID đội": "team_id",
    "MSSV": "mssv",
    "Họ và tên": "full_name",
    "Link Facebook": "facebook",
    "Trường": "school",
    "Khoa": "faculty",
    "Email": "email",
    "Số điện thoại": "phone",
}


async def fetch_sheet_values(api_key: str, sheet_id: str, range_name: str) -> Dict:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}?key={api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=30) as resp:
            resp.raise_for_status()
            return await resp.json()


def values_to_rows(values: List[List[str]]) -> List[Dict[str, str]]:
    if not values:
        return []
    headers = [h.strip() for h in values[0]]
    rows: List[Dict[str, str]] = []
    for r in values[1:]:
        mapped: Dict[str, str] = {}
        for idx, cell in enumerate(r):
            header = headers[idx] if idx < len(headers) else f"col_{idx}"
            dest = HEADER_MAP.get(header)
            if dest:
                mapped[dest] = (cell or "").strip()
        rows.append(mapped)
    return rows


def compute_hash(values: List[List[str]]) -> str:
    # Stable hash of the values payload
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def fetch_sheet_rows_and_hash(api_key: str, sheet_id: str, range_name: str) -> Tuple[List[Dict[str, str]], str]:
    data = await fetch_sheet_values(api_key, sheet_id, range_name)
    values = data.get("values", [])
    rows = values_to_rows(values)
    h = compute_hash(values)
    return rows, h

