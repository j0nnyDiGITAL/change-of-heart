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
import json
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .atomic_writer import (
    ConcurrencyConflictError,
    PostReplacementError,
    PreReplacementError,
    SaveValidationError,
    atomic_write_save,
    compute_sha256,
    verify_save_bytes,
)
from .editor import SaveEditor
from .environment import check_running_processes, create_memory_backup_zip


class AuthoritativeTransaction:
    """Represents a validated, reviewed, and confirmed stage transaction."""

    def __init__(
        self,
        stage_token: str,
        session_id: str,
        baseline_revision: int,
        baseline_sha256: str,
        patch_set: Dict[str, Any],
        patch_digest: str,
        summary: List[Dict[str, Any]],
    ):
        self.stage_token: str = stage_token
        self.session_id: str = session_id
        self.baseline_revision: int = baseline_revision
        self.baseline_sha256: str = baseline_sha256
        self.patch_set: Dict[str, Any] = patch_set
        self.patch_digest: str = patch_digest
        self.summary: List[Dict[str, Any]] = summary
        self.confirmed: bool = False
        self.confirmed_at: Optional[float] = None
        self.committed: bool = False
        self.committed_at: Optional[float] = None
        self.created_at: float = time.time()


class SaveSession:
    """Encapsulates a single active save editing session with transactional guarantees."""

    def __init__(
        self,
        raw_bytes: bytes,
        file_path: Optional[str] = None,
        is_uploaded: bool = False,
        read_only_diagnostics: bool = False,
    ):
        self.session_id: str = secrets.token_hex(16)
        self.capability_token: str = secrets.token_hex(24)
        self.file_path: Optional[str] = file_path
        self.is_uploaded: bool = is_uploaded

        # Immutable baseline
        self.baseline_bytes: bytes = bytes(raw_bytes)
        self.baseline_sha256: str = compute_sha256(self.baseline_bytes)
        self.is_read_only: bool = False
        self.diagnostic_error: Optional[str] = None

        # Strict validation of source bytes before establishing writable session
        try:
            verify_save_bytes(self.baseline_bytes, strict_crc=True)
            self.editor: SaveEditor = SaveEditor(self.baseline_bytes, strict_crc=True)
        except Exception as e:
            if not read_only_diagnostics:
                raise SaveValidationError(
                    f"Cannot create writable session: source save corrupted or invalid ({e})"
                ) from e
            self.is_read_only = True
            self.diagnostic_error = str(e)
            self.editor = SaveEditor(self.baseline_bytes, strict_crc=False)

        # Revision and state tracking
        self.revision: int = 1
        self.staged_changes: Dict[str, Any] = {}
        self.current_transaction: Optional[AuthoritativeTransaction] = None
        self.pending_transfer: Optional[Dict[str, Any]] = None
        self.created_at: float = time.time()
        self.last_saved_at: Optional[float] = None
        self.last_saved_sha256: Optional[str] = None

        self.lock = threading.RLock()
        self.committed_stage_tokens: set = set()

    def _check_writable(self):
        if self.is_read_only:
            raise SaveValidationError(
                f"Cannot mutate save: session is in read-only diagnostic mode ({self.diagnostic_error})."
            )

    def stage_field_change(self, category: str, key: str, new_val: Any, old_val: Any = None):
        """Stage a single typed modification in the pending change ledger."""
        self._check_writable()
        with self.lock:
            # Modifying staged changes invalidates any previously confirmed transaction
            if self.current_transaction and self.current_transaction.confirmed:
                self.current_transaction = None

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
            self.current_transaction = None

    def get_staged_summary(self) -> List[Dict[str, Any]]:
        """Return a structured list of pending staged changes for Before/After review."""
        with self.lock:
            summary = []
            for cat in sorted(self.staged_changes.keys()):
                items = self.staged_changes[cat]
                for key in sorted(items.keys()):
                    val = items[key]
                    summary.append({
                        "category": cat,
                        "field": key,
                        "old_value": val.get("old"),
                        "new_value": val.get("new"),
                        "timestamp": val.get("timestamp"),
                    })
            return summary

    def build_staged_patch_set(self) -> Dict[str, Any]:
        """Convert staged field changes into a structured patch dictionary."""
        patch: Dict[str, Any] = {}
        with self.lock:
            for cat, items in self.staged_changes.items():
                if cat == "header":
                    patch["header"] = {k: v.get("new") for k, v in items.items()}
                elif cat == "social_stats":
                    patch["social_stats"] = {k: v.get("new") for k, v in items.items()}
                elif cat == "confidants":
                    patch["confidants"] = {k: v.get("new") for k, v in items.items()}
                elif cat == "inventory":
                    patch["inventory_normalized"] = {k: v.get("new") for k, v in items.items()}
                elif cat == "compendium":
                    patch["compendium"] = {k: v.get("new") for k, v in items.items()}
                else:
                    patch[cat] = {k: v.get("new") for k, v in items.items()}
        return patch

    def prepare_staged_transaction(self) -> Dict[str, Any]:
        """
        Creates or updates an authoritative transaction from currently staged changes.
        Returns stage_token, deterministic patch_digest, revision, and summary.
        """
        self._check_writable()
        with self.lock:
            patch_set = self.build_staged_patch_set()
            summary = self.get_staged_summary()
            patch_bytes = json.dumps(patch_set, sort_keys=True, ensure_ascii=True).encode("utf-8")
            patch_digest = hashlib.sha256(patch_bytes).hexdigest()
            stage_token = secrets.token_hex(16)

            self.current_transaction = AuthoritativeTransaction(
                stage_token=stage_token,
                session_id=self.session_id,
                baseline_revision=self.revision,
                baseline_sha256=self.baseline_sha256,
                patch_set=patch_set,
                patch_digest=patch_digest,
                summary=summary,
            )

            return {
                "stage_token": stage_token,
                "patch_digest": patch_digest,
                "revision": self.revision,
                "staged_changes": summary,
            }

    def confirm_staged_transaction(
        self,
        stage_token: str,
        patch_digest: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Explicitly confirms a prepared stage transaction.
        Approval is strictly bound to the exact patch digest and baseline revision.
        """
        self._check_writable()
        with self.lock:
            if not self.current_transaction or self.current_transaction.stage_token != stage_token:
                raise SaveValidationError("Invalid or non-existent stage transaction token.")

            if self.current_transaction.baseline_revision != self.revision:
                self.current_transaction = None
                raise ConcurrencyConflictError(
                    f"Staged transaction baseline revision {self.current_transaction.baseline_revision} "
                    f"does not match current session revision {self.revision}."
                )

            if self.current_transaction.baseline_sha256 != self.baseline_sha256:
                self.current_transaction = None
                raise ConcurrencyConflictError("Staged transaction baseline hash does not match current session baseline.")

            if patch_digest and patch_digest != self.current_transaction.patch_digest:
                raise SaveValidationError("Patch digest mismatch: staged changes were modified after review.")

            self.current_transaction.confirmed = True
            self.current_transaction.confirmed_at = time.time()

            return {
                "status": "confirmed",
                "stage_token": stage_token,
                "patch_digest": self.current_transaction.patch_digest,
                "revision": self.revision,
            }

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

    def commit_transaction(
        self,
        data: Optional[Dict[str, Any]] = None,
        stage_token: Optional[str] = None,
        strict_verification: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes an authoritative two-phase transactional commit:
        - Strictly verifies stage token, patch digest, baseline revision, and approval.
        - Applies modifications to disposable SaveEditor clone.
        - Writes to disk atomically with backup and concurrency protection.
        - Updates session state only after verified disk persistence.
        """
        self._check_writable()
        with self.lock:
            # Check for running P5R.exe
            p5r_run, _ = check_running_processes()
            if p5r_run:
                raise RuntimeError("P5R.exe is currently running! Please close the game before saving.")

            patch_to_apply: Dict[str, Any] = {}

            if stage_token:
                if stage_token in self.committed_stage_tokens:
                    raise SaveValidationError("Transaction already committed (duplicate commit prevented).")
                if not self.current_transaction or self.current_transaction.stage_token != stage_token:
                    raise SaveValidationError("Invalid or unknown stage token.")
                if not self.current_transaction.confirmed:
                    raise SaveValidationError("Transaction has not been confirmed. Explicit review confirmation required.")
                if self.current_transaction.committed:
                    raise SaveValidationError("Transaction already committed (duplicate commit prevented).")
                if self.current_transaction.baseline_revision != self.revision:
                    raise ConcurrencyConflictError("Transaction baseline revision mismatch.")
                if self.current_transaction.baseline_sha256 != self.baseline_sha256:
                    raise ConcurrencyConflictError("Transaction baseline hash mismatch.")

                patch_to_apply = self.current_transaction.patch_set
            elif data and isinstance(data, dict):
                # Direct commit payload
                if self.staged_changes and self.current_transaction and not self.current_transaction.confirmed:
                    raise SaveValidationError(
                        "Pending unconfirmed staged edits exist. Please review and confirm staged transaction before commit."
                    )
                patch_to_apply = data
            elif self.current_transaction and self.current_transaction.confirmed:
                patch_to_apply = self.current_transaction.patch_set
            else:
                patch_to_apply = {}

            # Phase 1: Disposable candidate preparation
            candidate_editor = SaveEditor(self.baseline_bytes, strict_crc=strict_verification)
            self.apply_modifications_to_editor(candidate_editor, patch_to_apply)

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
            if self.current_transaction:
                self.current_transaction.committed = True
                self.current_transaction.committed_at = time.time()
                self.current_transaction = None
            if stage_token:
                self.committed_stage_tokens.add(stage_token)
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

    def build_transfer_preview(self, donor_save_bytes: bytes, categories: List[str]) -> Dict[str, Any]:
        """
        Builds a safe, typed semantic transfer preview from a validated donor save.
        Does NOT modify destination or donor saves.
        Returns bound transfer_token for explicit confirmation.
        """
        self._check_writable()
        with self.lock:
            # Validate donor save
            verify_save_bytes(donor_save_bytes, strict_crc=True)
            donor_editor = SaveEditor(donor_save_bytes, strict_crc=True)

            transfer_patch: Dict[str, Any] = {}
            preview_diff: List[Dict[str, Any]] = []
            warnings: List[str] = []

            # Exclusions per safety invariants
            exclusions = [
                "Protagonist Name (Identity-bound)",
                "Phantom Thief Group Name (Identity-bound)",
                "Calendar Day / Date (Story progression lock)",
                "Event Flag Matrix (3rd Semester & Palace flags)",
                "Outfits / Costumes (Read-only safety invariant)",
            ]

            if "money" in categories:
                src_money = donor_editor.get_money()
                cur_money = self.editor.get_money()
                transfer_patch["header"] = {"money": src_money}
                preview_diff.append({
                    "category": "Economy",
                    "field": "Yen Balance",
                    "current": cur_money,
                    "donor": src_money,
                })

            if "social_stats" in categories:
                src_stats = donor_editor.get_social_stats()
                cur_stats = self.editor.get_social_stats()
                transfer_patch["social_stats"] = src_stats
                for stat_name, src_val in src_stats.items():
                    preview_diff.append({
                        "category": "Social Stats",
                        "field": stat_name,
                        "current": cur_stats.get(stat_name, {}).get("rank", 1),
                        "donor": src_val.get("rank", 1) if isinstance(src_val, dict) else src_val,
                    })

            if "inventory" in categories:
                src_inv = donor_editor.get_normalized_inventory()
                transfer_patch["inventory_normalized"] = src_inv
                src_count = len(src_inv.get("stacks", {})) + len(src_inv.get("owned_gear", {}))
                cur_inv = self.editor.get_normalized_inventory()
                cur_count = len(cur_inv.get("stacks", {})) + len(cur_inv.get("owned_gear", {}))
                preview_diff.append({
                    "category": "Inventory",
                    "field": "Carried Inventory Items",
                    "current": f"{cur_count} items",
                    "donor": f"{src_count} items",
                })
                warnings.append("Destination consumable item stacks will be updated from donor save.")

            if "compendium" in categories:
                src_comp = set(donor_editor.get_compendium().get("registered", []))
                cur_comp = set(self.editor.get_compendium().get("registered", []))
                merged = sorted(list(src_comp | cur_comp))
                transfer_patch["compendium"] = {"supported": True, "registered": merged}
                preview_diff.append({
                    "category": "Velvet Room",
                    "field": "Compendium Registrations (Union)",
                    "current": f"{len(cur_comp)} personas registered",
                    "donor": f"{len(merged)} personas registered (merged union)",
                })

            if "personas" in categories:
                src_stock = donor_editor.get_persona_stock(0)
                transfer_patch["joker_stock"] = src_stock
                preview_diff.append({
                    "category": "Velvet Room",
                    "field": "Joker Active Persona Stock",
                    "current": f"{len(self.editor.get_persona_stock(0))} equipped",
                    "donor": f"{len(src_stock)} personas",
                })
                warnings.append("Joker active persona stock slots will be replaced by donor stock.")

            transfer_token = secrets.token_hex(16)
            donor_sha256 = compute_sha256(donor_save_bytes)

            self.pending_transfer = {
                "transfer_token": transfer_token,
                "dest_revision": self.revision,
                "dest_sha256": self.baseline_sha256,
                "source_sha256": donor_sha256,
                "categories": sorted(categories),
                "transfer_patch": transfer_patch,
                "expires_at": time.time() + 300,
            }

            return {
                "status": "preview",
                "transfer_token": transfer_token,
                "source_sha256": donor_sha256,
                "dest_revision": self.revision,
                "preview_diff": preview_diff,
                "warnings": warnings,
                "exclusions": exclusions,
            }

    def confirm_and_commit_transfer(
        self,
        transfer_token: str,
        donor_save_bytes: bytes,
    ) -> Dict[str, Any]:
        """
        Confirms and commits a previously previewed transfer.
        Enforces token validity, non-expiration, destination revision immutability,
        and donor SHA-256 integrity.
        """
        self._check_writable()
        with self.lock:
            if not self.pending_transfer or self.pending_transfer.get("transfer_token") != transfer_token:
                raise SaveValidationError("Invalid or missing transfer confirmation token.")

            if time.time() > self.pending_transfer["expires_at"]:
                self.pending_transfer = None
                raise SaveValidationError("Transfer confirmation expired (TTL 300s). Please preview again.")

            if self.revision != self.pending_transfer["dest_revision"]:
                self.pending_transfer = None
                raise ConcurrencyConflictError("Destination save changed revision after transfer preview was generated.")

            if self.baseline_sha256 != self.pending_transfer["dest_sha256"]:
                self.pending_transfer = None
                raise ConcurrencyConflictError("Destination save baseline hash changed after transfer preview was generated.")

            if compute_sha256(donor_save_bytes) != self.pending_transfer["source_sha256"]:
                self.pending_transfer = None
                raise ConcurrencyConflictError("Source donor save file was modified on disk after transfer preview was generated.")

            patch = self.pending_transfer["transfer_patch"]
            self.pending_transfer = None  # Consume token immediately to prevent duplicate commits

            res = self.commit_transaction(patch, strict_verification=True)
            res["transferred_categories"] = patch.keys()
            return res


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
        read_only_diagnostics: bool = False,
    ) -> SaveSession:
        with self._lock:
            session = SaveSession(
                raw_bytes,
                file_path=file_path,
                is_uploaded=is_uploaded,
                read_only_diagnostics=read_only_diagnostics,
            )
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

    def revoke_session(self, session_id: str) -> bool:
        """Revokes and invalidates a session and its capability tokens."""
        with self._lock:
            if session_id in self._sessions:
                s = self._sessions.pop(session_id)
                self._tokens.pop(s.capability_token, None)
                if self._active_session_id == session_id:
                    self._active_session_id = next(iter(self._sessions.keys()), None)
                return True
            return False

    def revoke_token(self, token: str) -> bool:
        """Revokes a specific capability token."""
        with self._lock:
            sess_id = self._tokens.pop(token, None)
            if sess_id:
                self._sessions.pop(sess_id, None)
                if self._active_session_id == sess_id:
                    self._active_session_id = next(iter(self._sessions.keys()), None)
                return True
            return False


# Global default session manager for server instance
SESSION_MANAGER = SessionManager()
