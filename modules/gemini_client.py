"""Module for interacting with the Gemini API using the google-genai SDK.

Supports conversational response generation as well as native Gemini Function Calling
(tool use) for executing Windows system tasks via modules.task_executor.
"""

import json
import os
import time
from typing import Any, Callable, Dict, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from modules.task_executor import (
    close_website,
    create_assignment_document,
    create_text_file,
    get_system_info,
    lock_computer,
    open_application,
    open_website,
    set_system_volume,
    take_screenshot,
)

# Load environment variables from .env file
load_dotenv()

# Primary and fallback model identifiers
PRIMARY_ACTION_MODEL = os.getenv("GEMINI_ACTION_MODEL", "gemini-3.5-flash-lite")
ACTION_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
]

PRIMARY_CONVERSATIONAL_MODEL = os.getenv("GEMINI_CONVERSATIONAL_MODEL", "gemini-3.5-flash-lite")
CONVERSATIONAL_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
]

# Dedicated high-depth model for document generation
PRIMARY_DOCUMENT_MODEL = os.getenv("GEMINI_DOCUMENT_MODEL", "gemini-3.5-flash-lite")
DOCUMENT_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
]

# Backward compatibility aliases
PRIMARY_MODEL = PRIMARY_CONVERSATIONAL_MODEL
FALLBACK_MODELS = CONVERSATIONAL_FALLBACK_MODELS

# System-level prompt for conversational TTS brevity and natural delivery (Spoken voice answers)
CONVERSATIONAL_SYSTEM_INSTRUCTION = (
    "You are Nexus, a smart and helpful voice assistant. "
    "Keep your spoken answers concise, direct, and conversational (typically 2 to 4 sentences), "
    "unless the user explicitly asks for more detail, code, or an in-depth explanation. "
    "Avoid unnecessary introductory filler."
)

# Dedicated system-level prompt for academic document and presentation generation (Detailed university-level assignments)
DOCUMENT_SYSTEM_INSTRUCTION = (
    "You are an academic writing assistant generating university-level assignment content. "
    "Write in a formal, well-structured, and thorough academic style suitable for a BSCS/undergraduate assignment. "
    "For each topic: "
    "- Provide a clear introduction/overview of the topic. "
    "- Break the content into logical sections/subtopics with proper headings. "
    "- Explain concepts in depth with sufficient detail, definitions, examples, and (where relevant) real-world applications or comparisons. "
    "- Use correct technical/academic terminology for the subject. "
    "- Include a brief conclusion/summary section at the end. "
    "- Do NOT keep explanations short — aim for genuine depth and completeness appropriate for a graded university assignment, not a quick conversational answer."
)


# Whitelisted action dispatch table for safe execution
ACTION_DISPATCH: Dict[str, Callable[..., str]] = {
    "open_application": open_application,
    "set_system_volume": set_system_volume,
    "lock_computer": lock_computer,
    "take_screenshot": take_screenshot,
    "open_website": open_website,
    "close_website": close_website,
    "get_system_info": get_system_info,
    "create_text_file": create_text_file,
    "create_assignment_document": create_assignment_document,
}

# Function schemas for Gemini function calling
ACTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="create_assignment_document",
        description="Creates and opens a Word document (.docx), PDF (.pdf), or PowerPoint presentation (.pptx) with detailed, university-level academic assignment content on a given topic.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "topic": types.Schema(
                    type=types.Type.STRING,
                    description="The subject or topic of the academic assignment (e.g. 'photosynthesis', 'French Revolution', 'climate change').",
                ),
                "doc_type": types.Schema(
                    type=types.Type.STRING,
                    enum=["docx", "pdf", "pptx"],
                    description="The requested output document format: 'docx' for Word document, 'pdf' for PDF document, or 'pptx' for PowerPoint presentation.",
                ),
            },
            required=["topic", "doc_type"],
        ),
    ),
    types.FunctionDeclaration(
        name="open_application",
        description="Opens a desktop Windows application such as Notepad, Calculator, Chrome, File Explorer, Terminal, Paint, or Settings. Do NOT use this for opening websites (use open_website for websites).",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "app_name": types.Schema(
                    type=types.Type.STRING,
                    description="The name of the desktop application to open (e.g. 'notepad', 'calculator', 'chrome', 'explorer').",
                )
            },
            required=["app_name"],
        ),
    ),
    types.FunctionDeclaration(
        name="set_system_volume",
        description="Sets the master Windows audio volume to a specific percentage level between 0 and 100.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "level": types.Schema(
                    type=types.Type.INTEGER,
                    description="Target audio volume level from 0 to 100.",
                )
            },
            required=["level"],
        ),
    ),
    types.FunctionDeclaration(
        name="lock_computer",
        description="Locks the active Windows computer workstation session.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
    types.FunctionDeclaration(
        name="take_screenshot",
        description="Captures a full screenshot of the screen and saves it with a timestamp into the safe Documents/Nexus folder.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
    types.FunctionDeclaration(
        name="open_website",
        description="Opens a website URL (e.g. 'youtube', 'github.com', 'google', 'reddit') or search query in a browser tab.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "url_or_search_term": types.Schema(
                    type=types.Type.STRING,
                    description="The website name/URL (e.g. 'youtube', 'github.com', 'https://reddit.com') or search keywords to look up.",
                )
            },
            required=["url_or_search_term"],
        ),
    ),
    types.FunctionDeclaration(
        name="close_website",
        description="Closes an open website, browser, or application window (e.g. 'instagram', 'youtube', 'github', 'reddit', 'chrome') by matching its visible window title.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "identifier": types.Schema(
                    type=types.Type.STRING,
                    description="The name, domain, or keyword of the website or application window to close (e.g. 'instagram', 'youtube', 'github', 'google').",
                )
            },
            required=["identifier"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_system_info",
        description="Returns system status information including current battery percentage, time, and date.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
    types.FunctionDeclaration(
        name="create_text_file",
        description="Creates a simple text file safely inside the Documents/Nexus folder with given filename and content.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "filename": types.Schema(
                    type=types.Type.STRING,
                    description="Name of the text file to create (e.g. 'notes.txt', 'todo.txt').",
                ),
                "content": types.Schema(
                    type=types.Type.STRING,
                    description="Text content to write into the file.",
                ),
            },
            required=["filename", "content"],
        ),
    ),
]


def _get_gemini_client() -> Optional[genai.Client]:
    """Retrieves an initialized google-genai Client or None if API key is missing."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("[Error: Gemini API] Missing or default placeholder GEMINI_API_KEY in .env file.")
        return None
    return genai.Client(api_key=api_key)


def generate_response(
    prompt: str, model: str = PRIMARY_CONVERSATIONAL_MODEL
) -> Optional[str]:
    """Sends a text prompt to Gemini API and returns concise conversational response text.

    Uses system instructions to keep answers concise (2 to 4 sentences) for natural voice playback.

    Args:
        prompt (str): The text input prompt.
        model (str): Gemini model identifier. Default is PRIMARY_CONVERSATIONAL_MODEL.

    Returns:
        Optional[str]: Response text returned by the model, or None if request fails.
    """
    client = _get_gemini_client()
    if client is None:
        return None

    config = types.GenerateContentConfig(
        system_instruction=CONVERSATIONAL_SYSTEM_INSTRUCTION,
        temperature=0.7,
    )

    # Try primary conversational model with automatic fallback on temporary server errors
    models_to_try = [model] + [m for m in CONVERSATIONAL_FALLBACK_MODELS if m != model]

    for target_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            return response.text
        except errors.APIError as err:
            print(f"[Error: Gemini API] API error on {target_model} (Status {err.code}): {err.message}")
            if err.code == 429:
                time.sleep(2.0)
        except Exception as err:
            print(f"[Error: Gemini API] Request error on {target_model}: {err}")

    return None


def route_to_action(user_text: str, model: str = PRIMARY_ACTION_MODEL) -> str:
    """Uses Gemini Function Calling on lightweight models to execute system tasks.

    1. Sends the user's text to Gemini with task executor tool declarations.
    2. If Gemini selects a function call, executes the corresponding whitelisted task function.
    3. If Gemini responds with plain text, returns that text as normal conversational fallback.
    4. Handles all exceptions gracefully with safe TTS-friendly error messages.

    Args:
        user_text (str): Spoken or typed user command.
        model (str): Target Gemini model identifier. Default is PRIMARY_ACTION_MODEL.

    Returns:
        str: Outcome description from the action or conversational response.
    """
    client = _get_gemini_client()
    if client is None:
        return "Sorry, Gemini API key is missing in your configuration."

    tool = types.Tool(function_declarations=ACTION_DECLARATIONS)
    config = types.GenerateContentConfig(
        tools=[tool],
        temperature=0.1,
    )

    # Try primary action model with lightweight fallback tier
    models_to_try = [model] + [m for m in ACTION_FALLBACK_MODELS if m != model]

    for target_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=user_text,
                config=config,
            )

            # Check if Gemini invoked a function call
            if response.function_calls:
                fc = response.function_calls[0]
                func_name = str(fc.name)
                func_args = dict(fc.args or {})
                print(f"[ACTION ROUTER] Gemini selected tool '{func_name}' with args: {func_args}")

                # Guardrail: Whitelist execution check
                if func_name not in ACTION_DISPATCH:
                    print(f"[ACTION ROUTER: ERROR] Requested tool '{func_name}' is not in allowed whitelist.")
                    return f"Sorry, action '{func_name}' is not supported."

                func = ACTION_DISPATCH[func_name]
                try:
                    # Execute whitelisted task function with extracted arguments
                    result = func(**func_args)
                    return str(result)
                except TypeError as type_err:
                    print(f"[ACTION ROUTER: ARG ERROR] Invalid arguments for '{func_name}': {type_err}")
                    return f"Sorry, I had trouble executing that command with the provided details."
                except Exception as exec_err:
                    print(f"[ACTION ROUTER: EXEC ERROR] Error running '{func_name}': {exec_err}")
                    return f"An error occurred while executing {func_name}: {exec_err}"

            # If no function call was generated, return plain text response
            if response.text:
                return response.text.strip()

            return "Command processed successfully."

        except errors.APIError as err:
            print(f"[Error: Gemini Action Router] API error on {target_model} (Status {err.code}): {err.message}")
            if err.code == 429:
                time.sleep(2.5)
        except Exception as err:
            print(f"[Error: Gemini Action Router] Exception on {target_model}: {err}")

    # Fallback to direct conversational response if function calling endpoint is temporarily unreachable
    fallback_text = generate_response(user_text)
    if fallback_text:
        return fallback_text

    return "Sorry, I am currently having trouble processing your command."


def generate_document_content(
    topic: str,
    doc_type: str = "docx",
    extra_instructions: Optional[str] = None,
    model: str = PRIMARY_DOCUMENT_MODEL,
) -> Optional[Dict[str, Any]]:
    """Generates detailed, university-level academic assignment or presentation content in structured JSON format.

    Uses a dedicated academic system instruction (DOCUMENT_SYSTEM_INSTRUCTION) to produce
    in-depth, rigorous content suitable for undergraduate-level documents.

    Args:
        topic (str): The subject or topic of the document (e.g. 'Photosynthesis', 'Deadlocks in Operating Systems').
        doc_type (str): Type of document ('docx', 'pdf', or 'pptx' / 'presentation'). Default is 'docx'.
        extra_instructions (Optional[str]): Any specific user preferences, focus areas, or constraints.
        model (str): Gemini model identifier. Default is PRIMARY_DOCUMENT_MODEL.

    Returns:
        Optional[Dict[str, Any]]: Structured JSON dictionary containing comprehensive document content, or None on failure.
    """
    client = _get_gemini_client()
    if client is None:
        return None

    normalized_type = doc_type.strip().lower()
    is_presentation = any(t in normalized_type for t in ["ppt", "presentation", "slide"])

    if is_presentation:
        user_prompt = (
            f"Generate a high-quality, university-level academic presentation slide deck on the topic: '{topic}'.\n\n"
            "Requirements:\n"
            "1. Output strictly valid JSON without markdown wrapping.\n"
            "2. Create 6 to 10 logically structured slides covering the topic thoroughly from fundamentals to advanced aspects.\n"
            "3. On-Slide Bullet Points: Keep bullet points clear, concise, and punchy (3 to 5 bullets per slide) so the slides remain visually readable without walls of text.\n"
            "4. Speaker Notes: Each slide MUST include a comprehensive, in-depth 'speaker_notes' field containing a detailed 2 to 4 paragraph academic explanation of that slide's concepts. This ensures full undergraduate-level rigor and completeness.\n\n"
            "JSON Format Schema:\n"
            "{\n"
            '  "title": "Comprehensive Academic Title",\n'
            '  "subtitle": "Undergraduate Presentation Subtitle",\n'
            '  "topic": "' + topic + '",\n'
            '  "target_audience": "Academic / Undergraduate Level",\n'
            '  "slides": [\n'
            "    {\n"
            '      "slide_number": 1,\n'
            '      "heading": "Slide Title / Topic",\n'
            '      "bullets": ["Concise on-slide point 1", "Concise on-slide point 2", "Concise on-slide point 3"],\n'
            '      "speaker_notes": "Comprehensive, multi-paragraph academic explanation providing deep background, mechanisms, and real-world significance for this slide."\n'
            "    }\n"
            "  ],\n"
            '  "summary_slide": {\n'
            '    "heading": "Conclusion & Summary",\n'
            '    "bullets": ["Summary point 1", "Summary point 2", "Summary point 3"],\n'
            '    "speaker_notes": "Comprehensive concluding remarks synthesizing the main academic insights."\n'
            "  }\n"
            "}"
        )
    else:
        user_prompt = (
            f"Generate a comprehensive, university-level academic assignment document on the topic: '{topic}'.\n\n"
            "Requirements:\n"
            "1. Output strictly valid JSON without markdown wrapping.\n"
            "2. Include a compelling academic title, subtitle, and an executive abstract/overview.\n"
            "3. Provide at least 5 to 7 extensive sequential sections exploring the topic thoroughly (e.g. Introduction & Background, Theoretical Foundations & Core Principles, Detailed Mechanisms / Subsystems, Real-World Applications & Case Studies, Comparative / Critical Analysis, Challenges & Future Directions).\n"
            "4. Each section MUST have substantial body text: multiple comprehensive paragraphs (2 to 4 substantial paragraphs per section) explaining concepts deeply with accurate technical terminology, definitions, equations/formulas (if applicable), and concrete examples. Avoid brief summaries or one-liners.\n"
            "5. Include a thorough Conclusion section and a list of academic References.\n\n"
            "JSON Format Schema:\n"
            "{\n"
            '  "title": "Comprehensive Academic Title",\n'
            '  "subtitle": "Undergraduate Assignment Subtitle",\n'
            '  "topic": "' + topic + '",\n'
            '  "abstract": "Comprehensive overview abstract paragraph...",\n'
            '  "sections": [\n'
            "    {\n"
            '      "heading": "Section Heading (e.g. 1. Introduction & Background)",\n'
            '      "subheading": "Optional Subheading",\n'
            '      "paragraphs": [\n'
            '        "Substantial academic paragraph 1 explaining the concept in rigorous detail...",\n'
            '        "Substantial academic paragraph 2 providing mechanics, theoretical foundations, or examples...",\n'
            '        "Substantial academic paragraph 3 discussing implications, edge cases, or applications..."\n'
            "      ],\n"
            '      "key_takeaways": ["Key takeaway point 1", "Key takeaway point 2"]\n'
            "    }\n"
            "  ],\n"
            '  "conclusion": "Comprehensive concluding evaluation synthesizing findings...",\n'
            '  "references": ["Academic Reference 1", "Academic Reference 2"]\n'
            "}"
        )

    if extra_instructions:
        user_prompt += f"\n\nSpecific Requirements & Guidelines from User:\n{extra_instructions}"

    config = types.GenerateContentConfig(
        system_instruction=DOCUMENT_SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        temperature=0.4,
    )

    models_to_try = [model] + [m for m in DOCUMENT_FALLBACK_MODELS if m != model]

    for target_model in models_to_try:
        try:
            print(f"[DOCUMENT GENERATOR] Generating {doc_type} content for '{topic}' using {target_model}...")
            response = client.models.generate_content(
                model=target_model,
                contents=user_prompt,
                config=config,
            )

            raw_text = response.text.strip() if response.text else ""
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            parsed_data = json.loads(raw_text)
            if isinstance(parsed_data, dict):
                print(f"[DOCUMENT GENERATOR: SUCCESS] Successfully generated content on {target_model}.")
                return parsed_data

        except json.JSONDecodeError as json_err:
            print(f"[DOCUMENT GENERATOR: PARSE ERROR] JSON decode error on {target_model}: {json_err}")
        except errors.APIError as err:
            print(f"[Error: Gemini Document Generator] API error on {target_model} (Status {err.code}): {err.message}")
            if err.code == 429:
                time.sleep(2.0)
        except Exception as err:
            print(f"[Error: Gemini Document Generator] Unexpected error on {target_model}: {err}")

    return None


if __name__ == "__main__":
    test_prompts = [
        "Open notepad for me",
        "Set the system volume to 35 percent",
        "What time is it and how is my battery?",
        "Who is Marie Curie?",
    ]
    for p in test_prompts:
        print(f"\nPrompt: '{p}'")
        res = route_to_action(p)
        print(f"Result: {res}")
