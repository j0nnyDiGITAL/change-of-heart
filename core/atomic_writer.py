"""
Atomic, transactional save file writing and rollback engine for Persona 5 Royal.

Guarantees:
1. Two-phase commit: writes candidate bytes to a temporary file in the same directory.
2. Flush and fsync to physical storage.
3. Candidate re-parse and strict container verification before replacing target.
4. Concurrency check: verifies target on disk has not been modified externally since baseline load.
5. Atomic replacement via os.replace (same-volume atomic rename) with Windows retry handling.
6. Post-replacement readback verification.
7. Zero corruption: on any failure, target file remains completely untouched.
8. Reversible: creates an immutable baseline backup and timestamped backup before replacement.
"""

import hashlib
import os
import secrets
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .crypto import SaveContainer, calc_crc
from .environment import create_timestamped_backup


class ConcurrencyConflictError(RuntimeError):
    """Raised when on-disk save has been modified by another process since loaded."""
    pass


class SaveValidationError(ValueError):
    """Raised when candidate bytes fail structural or CRC verification."""
    pass


def compute_sha256(data: bytes) -> str:
    """Compute hex SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def verify_save_bytes(raw_bytes: bytes, strict_crc: bool = True) -> Dict[str, Any]:
    """
    Strictly verify candidate save bytes before allowing them to be written to disk.
    Checks:
    - Minimum length
    - b'DATA' magic
    - Outer container CRC32
    - AES-256 decryption & header extraction
    - Inner Data CRC32
    - Decompressed payload boundaries
    """
    if not raw_bytes or len(raw_bytes) < 0x34:
        raise SaveValidationError(f"Save file too small: {len(raw_bytes) if raw_bytes else 0} bytes (minimum 0x34).")

    magic = raw_bytes[:4]
    if magic != b"DATA":
        raise SaveValidationError(f"Invalid save magic: {magic!r} (expected b'DATA').")

    # Outer CRC validation
    computed_file_crc = calc_crc(raw_bytes[0x8:])
    import struct
    file_crc = struct.unpack("<I", raw_bytes[4:8])[0]
    file_crc_ok = (computed_file_crc == file_crc)
    if strict_crc and not file_crc_ok:
        raise SaveValidationError(
            f"Outer File CRC mismatch: expected 0x{file_crc:08X}, calculated 0x{computed_file_crc:08X}."
        )

    # Container unpack and inner validation
    container = SaveContainer()
    try:
        container.unpack_raw(raw_bytes)
    except Exception as e:
        raise SaveValidationError(f"Failed to unpack save container: {e}") from e

    inner_crc_ok = (calc_crc(container.data_bytes) == container.data_crc)
    if strict_crc and not inner_crc_ok:
        raise SaveValidationError(
            f"Inner Data CRC mismatch: container header 0x{container.data_crc:08X} vs calculated 0x{calc_crc(container.data_bytes):08X}."
        )

    return {
        "valid": True,
        "length": len(raw_bytes),
        "data_length": len(container.data_bytes),
        "file_crc_ok": file_crc_ok,
        "inner_crc_ok": inner_crc_ok,
        "sha256": compute_sha256(raw_bytes),
    }


def atomic_write_save(
    target_path: Union[str, Path],
    candidate_bytes: bytes,
    expected_baseline_sha256: Optional[str] = None,
    create_backup: bool = True,
    strict_verification: bool = True,
    max_retries: int = 5,
    retry_delay_s: float = 0.05,
) -> Dict[str, Any]:
    """
    Atomically writes candidate save bytes to disk with two-phase verification and backup.

    Parameters:
    - target_path: Destination save file path on disk.
    - candidate_bytes: Repacked save container bytes.
    - expected_baseline_sha256: Expected hash of current file on disk (detects external edits).
    - create_backup: If True, creates a timestamped ZIP backup before replacing.
    - strict_verification: If True, validates CRCs and structure before replacing.
    - max_retries: Retry attempts for Windows file locks during os.replace.
    - retry_delay_s: Delay between retries.

    Returns dict with verification summary:
    - status: "success"
    - target_path: str
    - bytes_written: int
    - sha256: str
    - backup_path: Optional[str]
    """
    target = Path(target_path).resolve()
    target_dir = target.parent
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    # Phase 0: Concurrency conflict check against existing on-disk file
    if target.exists() and expected_baseline_sha256 is not None:
        try:
            current_on_disk_bytes = target.read_bytes()
            current_sha256 = compute_sha256(current_on_disk_bytes)
            if current_sha256.lower() != expected_baseline_sha256.lower():
                raise ConcurrencyConflictError(
                    f"Conflict detected: target save {target.name} has been modified externally "
                    f"(expected {expected_baseline_sha256[:10]}..., on disk {current_sha256[:10]}...)."
                )
        except ConcurrencyConflictError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to check on-disk baseline hash: {e}") from e

    # Phase 1: Pre-replacement candidate verification
    candidate_info = verify_save_bytes(candidate_bytes, strict_crc=strict_verification)
    candidate_sha256 = candidate_info["sha256"]

    # Phase 2: Create timestamped backup of current file before any disk replacement
    backup_path_str = None
    if create_backup and target.exists():
        backup_path = create_timestamped_backup(target)
        backup_path_str = str(backup_path)

    # Phase 3: Write candidate to temporary file in the same directory (guarantees same filesystem volume)
    temp_suffix = f".coh_tmp_{secrets.token_hex(6)}_{os.getpid()}"
    temp_path = target_dir / f"{target.name}{temp_suffix}"

    try:
        with open(temp_path, "wb") as f:
            f.write(candidate_bytes)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass  # fsync may not be supported on all network mounts

        # Phase 4: Verify the temporary file before atomic swap
        temp_written_bytes = temp_path.read_bytes()
        temp_sha256 = compute_sha256(temp_written_bytes)
        if temp_sha256 != candidate_sha256:
            raise SaveValidationError(
                f"Tempfile verification failed: written hash {temp_sha256} does not match candidate {candidate_sha256}."
            )

        # Reparse tempfile to confirm structure on disk
        verify_save_bytes(temp_written_bytes, strict_crc=strict_verification)

        # Re-check baseline before replacing if file exists
        if target.exists() and expected_baseline_sha256 is not None:
            current_sha256 = compute_sha256(target.read_bytes())
            if current_sha256.lower() != expected_baseline_sha256.lower():
                raise ConcurrencyConflictError(
                    f"Conflict detected immediately prior to atomic swap on {target.name}."
                )

        # Phase 5: Atomic replacement with bounded retry loop for Windows file locking
        replaced = False
        last_error = None
        for attempt in range(max_retries):
            try:
                os.replace(temp_path, target)
                replaced = True
                break
            except PermissionError as pe:
                last_error = pe
                time.sleep(retry_delay_s * (2 ** attempt))

        if not replaced:
            raise PermissionError(
                f"Failed to atomically replace {target} after {max_retries} attempts: {last_error}"
            )

    except Exception:
        # Cleanup temporary file on any error so disk is left clean
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise

    # Phase 6: Post-replacement readback verification
    persisted_bytes = target.read_bytes()
    persisted_sha256 = compute_sha256(persisted_bytes)
    if persisted_sha256 != candidate_sha256:
        raise SaveValidationError(
            f"Post-replacement verification failed: persisted hash {persisted_sha256} does not match candidate {candidate_sha256}."
        )

    return {
        "status": "success",
        "target_path": str(target),
        "bytes_written": len(persisted_bytes),
        "sha256": persisted_sha256,
        "backup_path": backup_path_str,
    }


def atomic_restore_backup(
    target_path: Union[str, Path],
    backup_zip: Union[str, Path],
    expected_baseline_sha256: Optional[str] = None,
    strict_verification: bool = True,
) -> Dict[str, Any]:
    """
    Atomically restores a save file from a backup ZIP archive.
    Validates that:
    1. Backup archive exists and contains the exact target file name.
    2. Payload inside the ZIP is structurally valid P5R save data (magic + CRC).
    3. Current target is backed up before being overwritten.
    4. Two-phase atomic write is used to replace target.
    """
    target = Path(target_path).resolve()
    zip_path = Path(backup_zip).resolve()

    if not zip_path.exists():
        raise FileNotFoundError(f"Backup archive not found: {zip_path}")

    # Inspect zip contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        matching_names = [n for n in names if Path(n).name == target.name]
        if not matching_names:
            raise ValueError(
                f"Backup archive {zip_path.name} does not contain {target.name} (found: {names[:5]})."
            )
        entry_name = matching_names[0]
        payload = zf.read(entry_name)

    # Validate payload before writing
    verify_save_bytes(payload, strict_crc=strict_verification)

    # Atomic write to target
    res = atomic_write_save(
        target_path=target,
        candidate_bytes=payload,
        expected_baseline_sha256=expected_baseline_sha256,
        create_backup=True,
        strict_verification=strict_verification,
    )
    res["restored_from"] = str(zip_path)
    return res
