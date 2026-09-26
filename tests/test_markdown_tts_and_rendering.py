"""Automated test suite for Markdown cleaning in Text-to-Speech and Frontend rendering."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.text_to_speech import clean_text_for_speech


def test_markdown_cleaning_comprehensive():
    print("\n" + "=" * 70)
    print("      TESTING MARKDOWN STRIPPING FOR TEXT-TO-SPEECH (TTS)          ")
    print("=" * 70)

    test_cases = [
        {
            "name": "Headings & Bold/Italics",
            "raw": "### Quantum Computing\n**Quantum computing** is a *rapidly-emerging* technology.",
            "must_not_contain": ["###", "**", "*"],
            "must_contain": ["Quantum Computing.", "Quantum computing is a rapidly-emerging technology."],
        },
        {
            "name": "Bullet Points & Lists",
            "raw": "Key features include:\n* Superposition\n- Entanglement\n+ Quantum tunneling",
            "must_not_contain": ["*", "-", "+"],
            "must_contain": ["Superposition.", "Entanglement.", "Quantum tunneling."],
        },
        {
            "name": "Inline Code & Code Blocks",
            "raw": "To run this, use `subprocess.run()`:\n```python\nimport sys\nprint('Hello World')\n```\nIt works reliably.",
            "must_not_contain": ["```", "`"],
            "must_contain": ["subprocess.run()", "import sys", "print('Hello World')", "It works reliably."],
        },
        {
            "name": "Links & Blockquotes",
            "raw": "> Note from documentation\nRead more at [Official Docs](https://example.com/docs).",
            "must_not_contain": [">", "[", "]", "(https://", "https://example.com/docs"],
            "must_contain": ["Note from documentation.", "Read more at Official Docs."],
        },
        {
            "name": "Markdown Tables & Dividers",
            "raw": "| Tool | Purpose |\n|---|---|\n| TTS | Speech Synthesis |\n\n---",
            "must_not_contain": ["|", "---"],
            "must_contain": ["Tool Purpose.", "TTS Speech Synthesis."],
        },
        {
            "name": "Punctuation Preservation",
            "raw": "What is Python? It's an awesome, high-level language! Do you agree?",
            "must_not_contain": ["**", "###"],
            "must_contain": ["What is Python?", "It's an awesome, high-level language!", "Do you agree?"],
        },
    ]

    for tc in test_cases:
        print(f"\n[Testing Case: {tc['name']}]")
        cleaned = clean_text_for_speech(tc["raw"])
        print(f"  Raw:     {tc['raw']!r}")
        print(f"  Cleaned: {cleaned!r}")

        for forbidden in tc["must_not_contain"]:
            assert forbidden not in cleaned, f"Forbidden string '{forbidden}' found in cleaned output: '{cleaned}'"

        for required in tc["must_contain"]:
            assert required in cleaned, f"Required string '{required}' missing in cleaned output: '{cleaned}'"

        print(f"  -> PASS: {tc['name']}")

    print("\n" + "=" * 70)
    print("      ALL MARKDOWN TTS CLEANING TESTS PASSED (100% SUCCESS)!      ")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    test_markdown_cleaning_comprehensive()
