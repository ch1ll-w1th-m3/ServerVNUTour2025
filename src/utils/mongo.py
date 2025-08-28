"""
MongoDB manager and sync utilities
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

try:
    from pymongo import MongoClient, UpdateOne
    from pymongo.collection import Collection
    from pymongo.errors import DuplicateKeyError
except Exception:  # pragma: no cover
    # Allow import of this file even if pymongo not installed yet
    MongoClient = None  # type: ignore
    UpdateOne = None  # type: ignore
    Collection = None  # type: ignore
    DuplicateKeyError = Exception  # type: ignore


class MongoManager:
    """MongoDB manager for participants and teams.

    Collections:
    - participants: one per MSSV, optional discord_id mapping
    - teams: team info aggregated by team_id
    """

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        # Use provided URI or get from environment (already loaded by config.py)
        self.uri = uri or os.getenv("MongoDB")
        self.db_name = db_name or os.getenv("MONGODB_DB_NAME", "vnutour")

        if not self.uri:
            raise RuntimeError("Thiếu biến môi trường MongoDB (URI) trong .env")

        if MongoClient is None:
            raise RuntimeError("Thiếu thư viện pymongo. Vui lòng `pip install -r requirements.txt`.")

        # Add connection timeout and server selection timeout
        self.client = MongoClient(
            self.uri,
            serverSelectionTimeoutMS=10000,  # 10 seconds timeout
            connectTimeoutMS=10000,          # 10 seconds connection timeout
            socketTimeoutMS=30000,           # 30 seconds socket timeout
            maxPoolSize=10,                  # Limit connection pool
            minPoolSize=1,                   # Minimum connections
            maxIdleTimeMS=30000,             # Close idle connections after 30s
            waitQueueTimeoutMS=5000,         # Wait queue timeout
            retryWrites=True,                # Enable retry for writes
            retryReads=True                  # Enable retry for reads
        )
        self.db = self.client[self.db_name]
        self.participants: Collection = self.db["participants"]
        self.teams: Collection = self.db["teams"]
        self.meta: Collection = self.db["meta"]

        # Test connection
        try:
            self.client.admin.command('ping')
            print("[DB] Kết nối MongoDB thành công")
        except Exception as e:
            print(f"[DB] Lỗi kết nối MongoDB: {e}")
            raise

        self._ensure_indexes()

    def is_healthy(self) -> bool:
        """Check if MongoDB connection is healthy"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def close(self):
        """Close MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()

    # ----- Indexes -----
    def _ensure_indexes(self):
        self.participants.create_index("mssv", unique=True)
        self.participants.create_index("discord_id", unique=True, sparse=True)
        self.teams.create_index("team_id", unique=True, sparse=True)
        self.teams.create_index("team_name")
        self.meta.create_index("key", unique=True)

    # ----- Normalizers -----
    @staticmethod
    def _norm_mssv(mssv: Any) -> str:
        return str(mssv).strip()

    @staticmethod
    def _digits(value: Any) -> Optional[str]:
        if value is None:
            return None
        s = re.sub(r"\D+", "", str(value))
        return s or None

    # ----- Participants -----
    def upsert_participant(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert participant by MSSV.

        Expected keys: mssv, full_name, email, phone, faculty, school, facebook, team_id, team_name
        """
        mssv = self._norm_mssv(data.get("mssv"))
        if not mssv:
            raise ValueError("Thiếu MSSV")

        doc = {
            "mssv": mssv,
            "full_name": (data.get("full_name") or "").strip(),
            "email": (data.get("email") or "").strip() or None,
            "phone": self._digits(data.get("phone")),
            "faculty": (data.get("faculty") or "").strip() or None,
            "school": (data.get("school") or "").strip() or None,
            "facebook": (data.get("facebook") or "").strip() or None,
            "team_id": (str(data.get("team_id")).strip() if data.get("team_id") not in (None, "") else None),
            "team_name": (data.get("team_name") or "").strip() or None,
            "updated_at": datetime.now(timezone.utc),
        }

        # Preserve existing discord_id if present
        existing = self.participants.find_one({"mssv": mssv}, {"discord_id": 1})
        if existing and existing.get("discord_id"):
            doc["discord_id"] = existing["discord_id"]

        self.participants.update_one({"mssv": mssv}, {"$set": doc}, upsert=True)
        return self.participants.find_one({"mssv": mssv}) or doc

    def assign_discord_by_mssv(self, mssv: str, discord_id: int) -> Tuple[str, str]:
        """Assign discord_id to a participant by MSSV.

        Returns (status, message) where status in {ok, not_found, already_assigned, already_linked, discord_already_used}.
        """
        mssv = self._norm_mssv(mssv)
        user = self.participants.find_one({"mssv": mssv})
        if not user:
            return ("not_found", f"Không tìm thấy MSSV {mssv} trong hệ thống.")

        # Check if this Discord ID is already used by another MSSV
        existing_discord_user = self.participants.find_one({"discord_id": int(discord_id)})
        if existing_discord_user and existing_discord_user.get("mssv") != mssv:
            return (
                "discord_already_used", 
                f"Discord ID của bạn đã được sử dụng bởi MSSV {existing_discord_user.get('mssv')} ({existing_discord_user.get('full_name', 'Không có tên')})."
            )

        current = user.get("discord_id")
        if current is None:
            try:
                self.participants.update_one(
                    {"mssv": mssv},
                    {"$set": {"discord_id": int(discord_id), "updated_at": datetime.now(timezone.utc)}},
                )
                return ("ok", f"Đã gán Discord cho MSSV {mssv}.")
            except Exception as e:
                if "E11000" in str(e):  # Duplicate key error
                    return (
                        "discord_already_used", 
                        f"Discord ID của bạn đã được sử dụng bởi MSSV khác. Vui lòng liên hệ admin để được hỗ trợ."
                    )
                return ("error", f"Lỗi khi gán Discord ID: {e}")

        if int(current) == int(discord_id):
            return ("already_linked", f"MSSV {mssv} đã liên kết với Discord của bạn.")

        return (
            "already_assigned",
            f"MSSV {mssv} đã được liên kết với tài khoản Discord khác.",
        )

    # ----- Teams -----
    def upsert_team(self, team_id: Optional[str], team_name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not team_id and not team_name:
            return None
        payload = {
            "team_id": (str(team_id).strip() if team_id not in (None, "") else None),
            "team_name": (team_name or "").strip() or None,
            "updated_at": datetime.now(timezone.utc),
        }
        key = {"team_id": payload["team_id"]} if payload["team_id"] else {"team_name": payload["team_name"]}
        self.teams.update_one(key, {"$set": payload}, upsert=True)
        return self.teams.find_one(key)

    # ----- Bulk sync from rows -----
    async def sync_from_rows_async(self, rows: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync many rows from a sheet-exported dataset asynchronously.

        Returns a summary dict.
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        updated = 0
        created = 0
        errors = 0
        
        # Use ThreadPoolExecutor to run MongoDB operations in background
        executor = ThreadPoolExecutor(max_workers=1)
        
        def sync_single_row(row_data):
            try:
                mssv = self._norm_mssv(row_data.get("mssv"))
                if not mssv:
                    return None, None
                    
                before = self.participants.find_one({"mssv": mssv})
                self.upsert_participant(row_data)
                
                # Upsert team and member mapping
                team_doc = self.upsert_team(row_data.get("team_id"), row_data.get("team_name"))
                if team_doc and mssv:
                    self.teams.update_one(
                        {"_id": team_doc["_id"]},
                        {"$addToSet": {"members_mssv": mssv}},
                    )
                    
                return before, None
                
            except Exception as e:
                return None, str(e)
        
        # Process rows in batches to avoid overwhelming the thread pool
        batch_size = 10
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            
            # Submit batch to thread pool
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, sync_single_row, row)
                for row in batch
            ]
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*futures, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    errors += 1
                    print(f"[SYNC ERROR] Row {i+j}: {result}")
                    continue
                    
                before, error = result
                if error:
                    errors += 1
                    print(f"[SYNC ERROR] Row {i+j}: {error}")
                    continue
                    
                if before:
                    updated += 1
                else:
                    created += 1
            
            # Small delay between batches to prevent overwhelming
            await asyncio.sleep(0.1)
        
        executor.shutdown(wait=False)
        return {"created": created, "updated": updated, "errors": errors}

    def sync_from_rows(self, rows: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync many rows from a sheet-exported dataset (synchronous version).

        Returns a summary dict.
        """
        updated = 0
        created = 0
        errors = 0
        
        for i, r in enumerate(rows):
            try:
                mssv = self._norm_mssv(r.get("mssv"))
                if not mssv:
                    continue
                    
                before = self.participants.find_one({"mssv": mssv})
                self.upsert_participant(r)
                if before:
                    updated += 1
                else:
                    created += 1

                # Upsert team and member mapping
                team_doc = self.upsert_team(r.get("team_id"), r.get("team_name"))
                if team_doc and mssv:
                    self.teams.update_one(
                        {"_id": team_doc["_id"]},
                        {"$addToSet": {"members_mssv": mssv}},
                    )
                    
            except Exception as e:
                errors += 1
                print(f"[SYNC ERROR] Row {i}: {e}")
                # Continue with next row instead of failing completely
                continue

        return {"created": created, "updated": updated, "errors": errors}

    # ----- Meta helpers -----
    def get_meta(self, key: str) -> Optional[Any]:
        doc = self.meta.find_one({"key": key})
        return doc.get("value") if doc else None

    def set_meta(self, key: str, value: Any) -> None:
        self.meta.update_one({"key": key}, {"$set": {"key": key, "value": value}}, upsert=True)
