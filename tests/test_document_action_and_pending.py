"""End-to-end verification tests for:
1. Document generation tool routing ('create_assignment_document' action).
2. Physical creation and opening of DOCX, PDF, and PPTX files.
3. Short-term pending action confirmation and cancellation memory.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from main import parse_intent, route_and_process
from modules.state import state
from modules.gemini_client import route_to_action, ACTION_DECLARATIONS, ACTION_DISPATCH
from modules.document_generator import DOCUMENTS_DIR, PROJECT_DOCS_DIR

load_dotenv()


def test_intent_parsing_for_documents():
    print("\n" + "=" * 70)
    print(" [1] TESTING INTENT PARSING FOR DOCUMENT COMMANDS")
    print("=" * 70)

    phrases = [
        "make me a PDF on photosynthesis",
        "create a word document about the French revolution",
        "make a presentation on climate change",
        "write an assignment on machine learning",
        "generate a pdf on computer architecture",
    ]

    for p in phrases:
        handler, topic = parse_intent(p)
        print(f"Phrase: '{p}' -> Handler: '{handler}'")
        assert handler == "Action", f"Expected 'Action' handler for '{p}', got '{handler}'"

    print("[PASS] All document commands correctly classified as 'Action' intent!")


def test_tool_declaration_and_dispatch():
    print("\n" + "=" * 70)
    print(" [2] TESTING ACTION TOOL DECLARATIONS & DISPATCH TABLE")
    print("=" * 70)

    assert "create_assignment_document" in ACTION_DISPATCH, "create_assignment_document missing from ACTION_DISPATCH"
    tool_names = [d.name for d in ACTION_DECLARATIONS]
    assert "create_assignment_document" in tool_names, "create_assignment_document missing from ACTION_DECLARATIONS"
    print(f"Found 'create_assignment_document' in ACTION_DECLARATIONS: {True}")
    print(f"Found 'create_assignment_document' in ACTION_DISPATCH: {True}")
    print("[PASS] Action declaration and dispatch verified!")


def test_document_creation_end_to_end():
    print("\n" + "=" * 70)
    print(" [3] TESTING PHYSICAL DOCUMENT CREATION VIA ACTION ROUTER")
    print("=" * 70)

    # Test 1: DOCX
    print("\n--> Test 1: Word Document on 'The French Revolution'")
    res_docx = route_and_process("create a word document about the French revolution")
    print(f"Result: {res_docx}")
    assert "ready" in res_docx.lower() or "created" in res_docx.lower(), f"DOCX generation failed: {res_docx}"

    # Test 2: PDF
    print("\n--> Test 2: PDF Document on 'Photosynthesis'")
    res_pdf = route_and_process("make me a PDF on photosynthesis")
    print(f"Result: {res_pdf}")
    assert "ready" in res_pdf.lower() or "created" in res_pdf.lower(), f"PDF generation failed: {res_pdf}"

    # Test 3: PPTX
    print("\n--> Test 3: Presentation on 'Climate Change'")
    res_pptx = route_and_process("make a presentation on climate change")
    print(f"Result: {res_pptx}")
    assert "ready" in res_pptx.lower() or "created" in res_pptx.lower(), f"PPTX generation failed: {res_pptx}"

    # Verify files created on disk
    target_dirs = [DOCUMENTS_DIR, PROJECT_DOCS_DIR]
    all_files = []
    for d in target_dirs:
        if d.exists():
            all_files.extend(list(d.glob("*.*")))

    print(f"\nGenerated files found on disk ({len(all_files)} total):")
    for f in all_files[-6:]:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")

    assert any(f.suffix == ".docx" for f in all_files), "No .docx files found in output directories"
    assert any(f.suffix == ".pdf" for f in all_files), "No .pdf files found in output directories"
    assert any(f.suffix == ".pptx" for f in all_files), "No .pptx files found in output directories"
    print("[PASS] All physical files (docx, pdf, pptx) created and verified on disk!")


def test_pending_action_memory():
    print("\n" + "=" * 70)
    print(" [4] TESTING SHORT-TERM PENDING ACTION MEMORY & CONFIRMATIONS")
    print("=" * 70)

    # Test 4A: Affirmative resolution ("yes do it")
    print("\n--> Test 4A: Setting pending action for 'Artificial Neural Networks' PDF & confirming with 'yes do it'")
    state.set_pending_action({
        "action": "create_assignment_document",
        "topic": "Artificial Neural Networks",
        "doc_type": "pdf"
    }, timeout_seconds=60)

    assert state.get_pending_action() is not None, "Pending action was not set"

    res_yes = route_and_process("yes do it")
    print(f"Response to 'yes do it': {res_yes}")
    assert "ready" in res_yes.lower() or "created" in res_yes.lower() or "pdf" in res_yes.lower(), f"Pending action confirmation failed: {res_yes}"
    assert state.get_pending_action() is None, "Pending action should be cleared after resolution"
    print("[PASS] Affirmative confirmation resolved successfully without repeating topic!")

    # Test 4B: Negative cancellation ("cancel")
    print("\n--> Test 4B: Setting pending action & cancelling with 'cancel'")
    state.set_pending_action({
        "action": "create_assignment_document",
        "topic": "Unwanted Topic",
        "doc_type": "docx"
    }, timeout_seconds=60)

    res_cancel = route_and_process("cancel")
    print(f"Response to 'cancel': {res_cancel}")
    assert "cancelled" in res_cancel.lower(), f"Expected cancellation response, got {res_cancel}"
    assert state.get_pending_action() is None, "Pending action should be cleared after cancellation"
    print("[PASS] Cancellation handled cleanly!")

    # Test 4C: Urdu affirmative confirmation ("haan")
    print("\n--> Test 4C: Setting pending action & confirming with Urdu 'haan'")
    state.set_pending_action({
        "action": "create_assignment_document",
        "topic": "Operating System Deadlocks",
        "doc_type": "docx"
    }, timeout_seconds=60)

    res_urdu = route_and_process("haan")
    print(f"Response to 'haan': {res_urdu}")
    assert "ready" in res_urdu.lower() or "word" in res_urdu.lower() or "created" in res_urdu.lower(), f"Urdu confirmation failed: {res_urdu}"
    print("[PASS] Multilingual confirmation ('haan') resolved successfully!")

    # Test 4D: Timeout expiration
    print("\n--> Test 4D: Testing pending action timeout expiration")
    state.set_pending_action({
        "action": "create_assignment_document",
        "topic": "Expired Topic",
        "doc_type": "docx"
    }, timeout_seconds=0.1)
    time.sleep(0.2)
    assert state.get_pending_action() is None, "Expired pending action should return None"
    print("[PASS] Pending action expired automatically after timeout!")


if __name__ == "__main__":
    print("=" * 70)
    print(" NEXUS DOCUMENT ACTION & PENDING CONFIRMATION TEST SUITE ")
    print("=" * 70)
    test_intent_parsing_for_documents()
    test_tool_declaration_and_dispatch()
    test_pending_action_memory()
    test_document_creation_end_to_end()
    print("\n" + "=" * 70)
    print("           ALL TESTS PASSED SUCCESSFULLY! (100%)       ")
    print("=" * 70)
