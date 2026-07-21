"""Refresh workflow: re-parse receipts already in the JSON store.

Receipts stay retrievable from the Lidl API long after purchase, so records
written by an older version of the parser can be rebuilt in place.  This is
how the discount backfill is done: receipts collected before per-line
discount parsing existed recorded the gross total as ``total_price``.
"""

from typing import Optional

from auth import setup_and_test_session
from storage import load_existing_receipts, sort_receipts_by_date
from .collector import fetch_and_store_receipts


def refresh_data(
    auth_method: Optional[str] = None,
    cookies_file: Optional[str] = None,
) -> bool:
    """
    Re-fetch and re-parse every receipt already present in the JSON file.

    Existing entries are replaced with the freshly parsed version; nothing is
    deleted, and receipts the API no longer serves are left untouched.

    Args:
        auth_method: Authentication method - 'firefox', 'chrome', 'chromium', or 'file'.
                     If None, prompts user interactively.
        cookies_file: Path to cookies file (only used when auth_method is 'file').

    Returns:
        bool: True if successful, False otherwise
    """
    print("=== REFRESH: Parse vorhandene Kassenbons neu ===")

    session = setup_and_test_session(auth_method, cookies_file)
    if not session:
        return False

    existing_ids, existing_receipts = load_existing_receipts()
    receipt_ids = [r.get("id") for r in existing_receipts if r.get("id")]

    print(f"Vorhandene Kassenbons zum Neuparsen: {len(receipt_ids)}")

    processed_count, skipped_count, total_items = fetch_and_store_receipts(
        session, receipt_ids
    )

    total_receipts = sort_receipts_by_date()

    print("\n=== REFRESH ABGESCHLOSSEN ===")
    print(f"Neu geparste Kassenbons: {processed_count}")
    print(f"Fehler/Uebersprungen: {skipped_count}")
    print(f"Verarbeitete Artikel: {total_items}")
    print(f"Gesamte Kassenbons in Datei: {total_receipts}")

    return True
