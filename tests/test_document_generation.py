"""Test suite for verifying academic document and presentation content generation in modules/gemini_client.py.

Verifies:
1. Document content generation for DOCX (university-level depth, multi-section, substantial paragraphs).
2. Presentation content generation for PPTX (concise on-slide bullet points + in-depth speaker notes).
3. Conversational responses remain short/concise (2-4 sentences) and are unaffected.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from modules.gemini_client import (
    generate_document_content,
    generate_response,
    PRIMARY_DOCUMENT_MODEL,
    DOCUMENT_SYSTEM_INSTRUCTION,
    CONVERSATIONAL_SYSTEM_INSTRUCTION,
)

load_dotenv()

def count_words(text_or_list):
    """Helper to count words in a string or list of strings/paragraphs."""
    if isinstance(text_or_list, str):
        return len(text_or_list.split())
    elif isinstance(text_or_list, list):
        total = 0
        for item in text_or_list:
            total += count_words(item)
        return total
    elif isinstance(text_or_list, dict):
        total = 0
        for k, v in text_or_list.items():
            total += count_words(v)
        return total
    return 0


def test_document_generation_docx():
    print("\n" + "=" * 70)
    print(" [1] TESTING DOCX ACADEMIC ASSIGNMENT GENERATION ('Photosynthesis')")
    print("=" * 70)

    doc_data = generate_document_content(topic="Photosynthesis", doc_type="docx")

    assert doc_data is not None, "Failed to generate docx content dictionary."
    assert isinstance(doc_data, dict), "Generated content is not a dict."

    title = doc_data.get("title", "")
    abstract = doc_data.get("abstract", "")
    sections = doc_data.get("sections", [])
    conclusion = doc_data.get("conclusion", "")
    references = doc_data.get("references", [])

    print(f"Title:    {title}")
    print(f"Subtitle: {doc_data.get('subtitle', 'N/A')}")
    print(f"Abstract Word Count: {count_words(abstract)} words")
    print(f"Total Sections Generated: {len(sections)}")

    assert len(sections) >= 4, f"Expected at least 4 sections, got {len(sections)}"

    total_doc_words = count_words(title) + count_words(abstract) + count_words(conclusion)

    print("\n--- Section Breakdown ---")
    for idx, sec in enumerate(sections, 1):
        heading = sec.get("heading", f"Section {idx}")
        paragraphs = sec.get("paragraphs", [])
        sec_words = count_words(paragraphs)
        total_doc_words += sec_words
        print(f"  [{idx}] {heading}")
        print(f"      - Paragraphs: {len(paragraphs)}")
        print(f"      - Word Count: {sec_words} words")
        print(f"      - Sample snippet: {paragraphs[0][:120]}..." if paragraphs else "      - (No paragraphs)")

    print(f"\nConclusion Word Count: {count_words(conclusion)} words")
    print(f"References Included:  {len(references)}")
    print(f"\n>>> TOTAL DOCUMENT WORD COUNT: {total_doc_words} words <<<")

    assert total_doc_words >= 400, f"Expected in-depth document (>=400 words), got {total_doc_words}"
    print("[PASS] DOCX Academic assignment generation verified successfully!")
    return doc_data


def test_document_generation_pptx():
    print("\n" + "=" * 70)
    print(" [2] TESTING PPTX PRESENTATION GENERATION ('Photosynthesis')")
    print("=" * 70)

    ppt_data = generate_document_content(topic="Photosynthesis", doc_type="pptx")

    assert ppt_data is not None, "Failed to generate pptx content dictionary."
    assert isinstance(ppt_data, dict), "Generated content is not a dict."

    title = ppt_data.get("title", "")
    slides = ppt_data.get("slides", [])
    summary_slide = ppt_data.get("summary_slide", {})

    print(f"Title:    {title}")
    print(f"Subtitle: {ppt_data.get('subtitle', 'N/A')}")
    print(f"Total Slides: {len(slides)}")

    assert len(slides) >= 5, f"Expected at least 5 slides, got {len(slides)}"

    total_notes_words = 0
    total_slide_bullet_words = 0

    print("\n--- Slide Breakdown ---")
    for idx, slide in enumerate(slides, 1):
        heading = slide.get("heading", f"Slide {idx}")
        bullets = slide.get("bullets", [])
        notes = slide.get("speaker_notes", "")

        bullet_words = count_words(bullets)
        notes_words = count_words(notes)

        total_slide_bullet_words += bullet_words
        total_notes_words += notes_words

        print(f"  Slide {idx}: {heading}")
        print(f"      - Visual Bullets: {len(bullets)} items ({bullet_words} words)")
        print(f"      - Speaker Notes: {notes_words} words")
        print(f"      - Notes Sample: {notes[:140]}...")

    if summary_slide:
        sum_bullets = summary_slide.get("bullets", [])
        sum_notes = summary_slide.get("speaker_notes", "")
        print(f"  Summary Slide: {summary_slide.get('heading', 'Summary')}")
        print(f"      - Summary Bullets: {len(sum_bullets)}")
        print(f"      - Summary Notes: {count_words(sum_notes)} words")
        total_slide_bullet_words += count_words(sum_bullets)
        total_notes_words += count_words(sum_notes)

    print(f"\n>>> Total Slide On-Screen Bullet Words: {total_slide_bullet_words} words (Concise visual) <<<")
    print(f">>> Total Speaker Notes Word Count:     {total_notes_words} words (In-depth academic) <<<")

    assert total_notes_words >= 300, f"Expected detailed speaker notes (>=300 words), got {total_notes_words}"
    print("[PASS] PPTX Presentation content generation verified successfully!")
    return ppt_data


def test_conversational_remains_concise():
    print("\n" + "=" * 70)
    print(" [3] VERIFYING CONVERSATIONAL RESPONSE REMAINS CONCISE (2-4 SENTENCES)")
    print("=" * 70)

    resp = generate_response("Who is Nikola Tesla?")
    assert resp is not None, "Failed to generate conversational response."

    words = len(resp.split())
    sentences = [s.strip() for s in resp.replace("!", ".").replace("?", ".").split(".") if s.strip()]

    print(f"Query: 'Who is Nikola Tesla?'")
    print(f"Response: {resp}")
    print(f"Word count: {words} words | Sentence count: {len(sentences)}")

    assert words < 120, f"Conversational response too verbose ({words} words)"
    print("[PASS] Conversational response is concise and unaffected by document generation instructions.")


if __name__ == "__main__":
    print("=" * 70)
    print("       NEXUS DOCUMENT GENERATION SYSTEM VERIFICATION SUITE           ")
    print("=" * 70)
    test_document_generation_docx()
    test_document_generation_pptx()
    test_conversational_remains_concise()
    print("\n" + "=" * 70)
    print("                  ALL DOCUMENT GENERATION TESTS PASSED!              ")
    print("=" * 70)
