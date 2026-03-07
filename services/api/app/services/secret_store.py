from __future__ import annotations

import base64
import sys
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSecret


@dataclass(frozen=True)
class StoredSecret:
    """Container for encrypted and decrypted secret values."""
    value: str
    storage: Literal["dpapi", "plaintext"]


def _encrypt_windows_dpapi(plaintext: str) -> str:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        """Data model for data blob."""
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    def blob_from_bytes(data: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
        buf = ctypes.create_string_buffer(data)
        return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf

    in_blob, _in_buf = blob_from_bytes(plaintext.encode("utf-8"))
    out_blob = DATA_BLOB()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise RuntimeError("CryptProtectData failed")
    try:
        encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return "dpapi:" + base64.b64encode(encrypted).decode("ascii")


def _decrypt_windows_dpapi(ciphertext: str) -> str:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        """Data model for data blob."""
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    data = base64.b64decode(ciphertext.split(":", 1)[1].encode("ascii"))

    def blob_from_bytes(raw: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
        buf = ctypes.create_string_buffer(raw)
        return DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf

    in_blob, _in_buf = blob_from_bytes(data)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise RuntimeError("CryptUnprotectData failed")
    try:
        decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return decrypted.decode("utf-8")


def _encrypt_local(plaintext: str) -> tuple[str, Literal["dpapi", "plaintext"]]:
    if sys.platform.startswith("win"):
        return _encrypt_windows_dpapi(plaintext), "dpapi"
    # Non-windows fallback keeps compatibility in CI/containers.
    encoded = base64.b64encode(plaintext.encode("utf-8")).decode("ascii")
    return f"plain:{encoded}", "plaintext"


def _decrypt_local(ciphertext: str) -> StoredSecret:
    if ciphertext.startswith("dpapi:"):
        return StoredSecret(value=_decrypt_windows_dpapi(ciphertext), storage="dpapi")
    if ciphertext.startswith("plain:"):
        raw = base64.b64decode(ciphertext.split(":", 1)[1].encode("ascii")).decode("utf-8")
        return StoredSecret(value=raw, storage="plaintext")
    raise ValueError("Unknown secret encoding format")


def set_secret(db: Session, key: str, plaintext: str) -> Literal["dpapi", "plaintext"]:
    encrypted_value, storage = _encrypt_local(plaintext)
    row = db.scalar(select(AppSecret).where(AppSecret.secret_key == key))
    if row is None:
        row = AppSecret(secret_key=key, encrypted_value=encrypted_value)
        db.add(row)
    else:
        row.encrypted_value = encrypted_value
    db.flush()
    return storage


def get_secret(db: Session, key: str) -> StoredSecret | None:
    row = db.scalar(select(AppSecret).where(AppSecret.secret_key == key))
    if row is None:
        return None
    return _decrypt_local(row.encrypted_value)


def clear_secret(db: Session, key: str) -> bool:
    row = db.scalar(select(AppSecret).where(AppSecret.secret_key == key))
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True

