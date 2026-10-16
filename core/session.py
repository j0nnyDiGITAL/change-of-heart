"""
Transactional Save Session Manager for Persona 5 Royal Save Studio.

Replaces unsafe global mutable state with isolated, capability-secured sessions:
1. Each loaded save receives a unique session_id and process-local capability_token.
2. Immutable baseline bytes and baseline SHA-256 protect against race conditions and external overwrites.
3. Revision counter increments only on successful verified disk commit.
4. Two-phase candidate application: all edits are staged and validated against a disposable
   SaveEditor clone. The active session editor is updated ONLY after physical verification succeeds.
5. Concurrency protection: detects external modifications and prevents last-write-wins collisions (HTTP 409).
"""

import base64
import copy
import hashlib
import os
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .atomic_writer import (
    ConcurrencyConflictError,
    SaveValidationError,
    atomic_write_save,
    compute_sha256,
    verify_save_bytes,
)
from .editor import SaveEditor
from .environment import check_running_processes, create_memory_backup_zip


class SaveSession:
    """Encapsulates a single active save editing session with transactional guarantees."""

    def __init__(
        self,
        raw_bytes: bytes,
        file_path: Optional[str] = None,
        is_uploaded: bool = False,
    ):
        self.session_id: str = secrets.token_hex(16)
        self.capability_token: str = secrets.token_hex(24)
        self.file_path: Optional[str] = file_path
        self.is_uploaded: bool = is_uploaded

        # Immutable baseline
        self.baseline_bytes: bytes = bytes(raw_bytes)
        self.baseline_sha256: str = compute_sha256(self.baseline_bytes)

        # Active editor instance
        self.editor: SaveEditor = SaveEditor(self.baseline_bytes)

        # Revision and state tracking
        self.revision: int = 1
        self.staged_changes: Dict[str, Any] = {}
        self.created_at: float = time.time()
        self.last_saved_at: Optional[float] = None
        self.last_saved_sha256: Optional[str] = None

        self.lock = threading.RLock()

    def stage_field_change(self, category: str, key: str, new_val: Any, old_val: Any = None):
        """Stage a single typed modification in the pending change ledger."""
        with self.lock:
            if category not in self.staged_changes:
                self.staged_changes[category] = {}
            self.staged_changes[category][key] = {
                "new": new_val,
                "old": old_val,
                "timestamp": time.time(),
            }

    def clear_staged_changes(self):
        """Discard all pending staged changes without touching baseline."""
        with self.lock:
            self.staged_changes.clear()

    def get_staged_summary(self) -> List[Dict[str, Any]]:
        """Return a structured list of pending staged changes for Before/After review."""
        with self.lock:
            summary = []
            for cat, items in self.staged_changes.items():
                for key, val in items.items():
                    summary.append({
                        "category": cat,
                        "field": key,
                        "old_value": val.get("old"),
                        "new_value": val.get("new"),
                        "timestamp": val.get("timestamp"),
                    })
            return summary

    def apply_modifications_to_editor(self, target_editor: SaveEditor, data: Dict[str, Any]):
        """
        Applies a validated dictionary of modifications to a target SaveEditor instance.
        Executed against a disposable clone during transaction verification.
        """
        # 1. Player & Thieves Names and Money
        hdr_in = data.get("header", {})
        if hdr_in:
            in_fname = str(hdr_in.get("fname", target_editor.parser.header.fname)).strip()
            in_lname = str(hdr_in.get("lname", target_editor.parser.header.lname)).strip()
            in_group = str(hdr_in.get("group_name", target_editor.parser.player_names.group_name_utf8)).strip()
            if (
                in_fname != target_editor.parser.header.fname
                or in_lname != target_editor.parser.header.lname
                or in_group != target_editor.parser.player_names.group_name_utf8
            ):
                target_editor.set_player_names(in_fname, in_lname, in_group)
            if "money" in hdr_in:
                target_editor.set_money(int(hdr_in["money"]))

        # 2. Social Stats
        soc_in = data.get("social_stats", {})
        if soc_in:
            def _extract_stat_rank(val):
                if isinstance(val, dict):
                    return int(val.get("rank", 5))
                return int(val) if val is not None else 5

            target_editor.set_social_stats(
                _extract_stat_rank(soc_in.get("Knowledge", 5)),
                _extract_stat_rank(soc_in.get("Charm", 5)),
                _extract_stat_rank(soc_in.get("Proficiency", 5)),
                _extract_stat_rank(soc_in.get("Kindness", 5)),
                _extract_stat_rank(soc_in.get("Guts", 5)),
            )

        # 3. Confidants
        conf_in = data.get("confidants", {})
        if conf_in:
            from .editor import CONFIDANT_ARCANA_MAP
            for cname, cdata in conf_in.items():
                if cname in CONFIDANT_ARCANA_MAP:
                    arc_id = CONFIDANT_ARCANA_MAP[cname]
                    rank = int(cdata.get("rank", 0)) if isinstance(cdata, dict) else int(cdata)
                    romance = bool(cdata.get("romance", False)) if isinstance(cdata, dict) and "romance" in cdata else None
                    target_editor.set_confidant_rank(arc_id, rank, romance=romance, auto_unlock=True)

        # 4. Party Stats & Equipped Persona
        party_in = data.get("party", [])
        for member in party_in:
            slot = member.get("slot")
            if slot is not None:
                target_editor.set_party_stat(
                    slot,
                    level=int(member.get("level", 1)),
                    hp=int(member.get("hp", 100)),
                    sp=int(member.get("sp", 50)),
                )
                pers = member.get("persona")
                if pers and "persona_id" in pers:
                    raw_skills = pers.get("skills", [0] * 8)
                    parsed_skills = []
                    for s in raw_skills:
                        if isinstance(s, dict):
                            parsed_skills.append(int(s.get("id", 0)))
                        else:
                            parsed_skills.append(int(s) if s is not None else 0)

                    raw_stats = pers.get("stats", [10] * 5)
                    if isinstance(raw_stats, dict):
                        parsed_stats = [
                            int(raw_stats.get("st", 10)),
                            int(raw_stats.get("ma", 10)),
                            int(raw_stats.get("en", 10)),
                            int(raw_stats.get("ag", 10)),
                            int(raw_stats.get("lu", 10)),
                        ]
                    elif isinstance(raw_stats, list):
                        parsed_stats = [int(st) if st is not None else 10 for st in raw_stats]
                    else:
                        parsed_stats = [10] * 5

                    target_editor.set_equipped_persona(
                        slot,
                        persona_id=int(pers.get("persona_id", 0)),
                        level=int(pers.get("level", 1)),
                        trait_id=int(pers.get("trait_id", 0)),
                        exp=int(pers.get("exp", 0)),
                        skills=parsed_skills,
                        stats=parsed_stats,
                        flags=int(pers.get("flags", 1)),
                    )

        # 5. Joker Persona Stock (12 slots)
        stock_in = data.get("joker_stock", [])
        for s_entry in stock_in:
            s_slot = s_entry.get("slot")
            if s_slot is not None and 0 <= s_slot < 12:
                pid = int(s_entry.get("persona_id", 0))
                raw_skills = s_entry.get("skills", [0] * 8)
                parsed_skills = []
                for s in raw_skills:
                    if isinstance(s, dict):
                        parsed_skills.append(int(s.get("id", 0)))
                    else:
                        parsed_skills.append(int(s) if s is not None else 0)

                raw_stats = s_entry.get("stats", [10] * 5)
                if isinstance(raw_stats, dict):
                    parsed_stats = [
                        int(raw_stats.get("st", 10)),
                        int(raw_stats.get("ma", 10)),
                        int(raw_stats.get("en", 10)),
                        int(raw_stats.get("ag", 10)),
                        int(raw_stats.get("lu", 10)),
                    ]
                elif isinstance(raw_stats, list):
                    parsed_stats = [int(st) if st is not None else 10 for st in raw_stats]
                else:
                    parsed_stats = [10] * 5

                target_editor.set_persona_stock_slot(
                    member_slot=0,
                    stock_k=s_slot,
                    persona_id=pid,
                    level=int(s_entry.get("level", 1)),
                    trait_id=int(s_entry.get("trait_id", 0)),
                    exp=int(s_entry.get("exp", 0)),
                    skills=parsed_skills,
                    stats=parsed_stats,
                    flags=int(s_entry.get("flags", 1)),
                )

        # 6. Active Inventory Items
        norm_in = data.get("inventory_normalized")
        if isinstance(norm_in, dict):
            for raw_id, qty in (norm_in.get("stacks") or {}).items():
                try:
                    iid = int(raw_id)
                except Exception:
                    continue
                target_editor.set_item_quantity(iid, int(qty))
            for raw_id, owned in (norm_in.get("owned_gear") or {}).items():
                try:
                    iid = int(raw_id)
                except Exception:
                    continue
                target_editor.set_item_quantity(iid, 1 if owned else 0)
        elif "inventory" in data:
            for entry in data.get("inventory", []):
                iid = int(entry.get("item_id", 0))
                qty = int(entry.get("quantity", 0))
                slot = entry.get("slot")
                if iid > 0:
                    if slot is not None and 0 <= slot < 30:
                        target_editor.set_inventory_slot(slot, iid, qty)
                    else:
                        target_editor.set_item_quantity(iid, qty)

        # 7. Compendium Registration
        if data.get("unlock_compendium"):
            target_editor.unlock_compendium_100()
        elif "compendium" in data and isinstance(data["compendium"], dict):
            comp = data["compendium"]
            if comp and comp.get("supported"):
                registered_list = set(comp.get("registered", []))
                current_reg = set(target_editor.get_compendium().get("registered", []))
                changed_pids = sorted(registered_list ^ current_reg)
                if changed_pids:
                    for pid in changed_pids:
                        is_reg = pid in registered_list
                        target_editor.set_compendium_registration(pid, is_reg)

    def commit_transaction(self, data: Dict[str, Any], strict_verification: bool = True) -> Dict[str, Any]:
        """
        Executes a two-phase transactional commit:
        Phase 1: Clone baseline editor and apply all modifications.
        Phase 2: Pack and cryptographically resign candidate save bytes.
        Phase 3: Write to disk atomically with backup and concurrency protection.
        Phase 4: Update session state ONLY after verified write succeeds.
        """
        with self.lock:
            # Check for running P5R.exe
            p5r_run, _ = check_running_processes()
            if p5r_run:
                raise RuntimeError("P5R.exe is currently running! Please close the game before saving.")

            # Phase 1: Disposable candidate preparation
            candidate_editor = SaveEditor(self.baseline_bytes)
            self.apply_modifications_to_editor(candidate_editor, data)

            # Phase 2: Pack & Sign candidate container
            candidate_bytes = candidate_editor.save_to_bytes()

            # Phase 3: Physical Persistence
            backup_path_name = "N/A (Uploaded save)"
            backup_zip_b64 = None
            backup_zip_filename = None

            if not self.is_uploaded and self.file_path:
                write_result = atomic_write_save(
                    target_path=self.file_path,
                    candidate_bytes=candidate_bytes,
                    expected_baseline_sha256=self.baseline_sha256,
                    create_backup=True,
                    strict_verification=strict_verification,
                )
                if write_result.get("backup_path"):
                    backup_path_name = Path(write_result["backup_path"]).name
            else:
                # In-memory backup zip for uploaded files
                save_name = (self.file_path or "DATA.DAT").replace("Uploaded (", "").replace(")", "").strip() or "DATA.DAT"
                zip_bytes = create_memory_backup_zip(self.baseline_bytes, filename=save_name)
                backup_zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
                stem = Path(save_name).stem
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_zip_filename = f"{stem}_backup_{timestamp}.zip"
                backup_path_name = backup_zip_filename

            # Phase 4: State commit — authoritative switch
            self.baseline_bytes = candidate_bytes
            self.baseline_sha256 = compute_sha256(candidate_bytes)
            self.editor = candidate_editor
            self.revision += 1
            self.staged_changes.clear()
            self.last_saved_at = time.time()
            self.last_saved_sha256 = self.baseline_sha256

            integrity = self.editor.integrity_report()

            return {
                "status": "success",
                "revision": self.revision,
                "session_id": self.session_id,
                "sha256": self.baseline_sha256,
                "backup": backup_path_name,
                "backup_zip_name": backup_zip_filename,
                "backup_zip_data": backup_zip_b64,
                "integrity": integrity,
                "download_data": base64.b64encode(candidate_bytes).decode("ascii") if self.is_uploaded else None,
                "message": "Save file successfully verified, re-signed, and committed!",
            }


class SessionManager:
    """Thread-safe manager for save editing sessions."""

    def __init__(self):
        self._sessions: Dict[str, SaveSession] = {}
        self._tokens: Dict[str, str] = {}  # token -> session_id
        self._active_session_id: Optional[str] = None
        self._lock = threading.RLock()

    def create_session(
        self,
        raw_bytes: bytes,
        file_path: Optional[str] = None,
        is_uploaded: bool = False,
    ) -> SaveSession:
        with self._lock:
            session = SaveSession(raw_bytes, file_path=file_path, is_uploaded=is_uploaded)
            self._sessions[session.session_id] = session
            self._tokens[session.capability_token] = session.session_id
            self._active_session_id = session.session_id
            return session

    def get_session(self, session_id: Optional[str] = None) -> Optional[SaveSession]:
        with self._lock:
            if session_id:
                return self._sessions.get(session_id)
            if self._active_session_id:
                return self._sessions.get(self._active_session_id)
            return None

    def get_session_by_token(self, token: Optional[str]) -> Optional[SaveSession]:
        with self._lock:
            if not token:
                return None
            sess_id = self._tokens.get(token)
            return self._sessions.get(sess_id) if sess_id else None

    def validate_capability(self, token: Optional[str], session_id: Optional[str] = None) -> bool:
        """Validates that the provided capability token grants access to the session."""
        with self._lock:
            if not token:
                return False
            bound_id = self._tokens.get(token)
            if not bound_id:
                return False
            if session_id and bound_id != session_id:
                return False
            return True


# Global default session manager for server instance
SESSION_MANAGER = SessionManager()
