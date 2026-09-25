"""Module for interacting with the Gemini API using the google-genai SDK.

Supports conversational response generation as well as native Gemini Function Calling
(tool use) for executing Windows system tasks via modules.task_executor.
"""

import os
from typing import Any, Callable, Dict, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from modules.task_executor import (
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
PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-3.8-flash"

# Whitelisted action dispatch table for safe execution
ACTION_DISPATCH: Dict[str, Callable[..., str]] = {
    "open_application": open_application,
    "set_system_volume": set_system_volume,
    "lock_computer": lock_computer,
    "take_screenshot": take_screenshot,
    "open_website": open_website,
    "get_system_info": get_system_info,
    "create_text_file": create_text_file,
}

# Function schemas for Gemini function calling
ACTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="open_application",
        description="Opens a common Windows desktop application such as Notepad, Calculator, Chrome, File Explorer, Terminal, Paint, or Settings.",
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
        description="Captures a full screenshot of the screen and saves it with a timestamp into the safe Documents/Aetheris folder.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
    types.FunctionDeclaration(
        name="open_website",
        description="Opens a website URL or searches Google in the default web browser.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "url_or_search_term": types.Schema(
                    type=types.Type.STRING,
                    description="The website URL (e.g. 'youtube.com', 'https://github.com') or search keywords to look up.",
                )
            },
            required=["url_or_search_term"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_system_info",
        description="Returns system status information including current battery percentage, time, and date.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
    types.FunctionDeclaration(
        name="create_text_file",
        description="Creates a simple text file safely inside the Documents/Aetheris folder with given filename and content.",
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
    prompt: str, model: str = PRIMARY_MODEL
) -> Optional[str]:
    """Sends a text prompt to Gemini API and returns conversational response text.

    Args:
        prompt (str): The text input prompt.
        model (str): Gemini model identifier. Default is 'gemini-3.6-flash'.

    Returns:
        Optional[str]: Response text returned by the model, or None if request fails.
    """
    client = _get_gemini_client()
    if client is None:
        return None

    # Try primary model with automatic fallback on temporary server errors
    models_to_try = [model]
    if FALLBACK_MODEL not in models_to_try:
        models_to_try.append(FALLBACK_MODEL)

    for target_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
            )
            return response.text
        except errors.APIError as err:
            print(f"[Error: Gemini API] API error on {target_model} (Status {err.code}): {err.message}")
        except Exception as err:
            print(f"[Error: Gemini API] Request error on {target_model}: {err}")

    return None


def route_to_action(user_text: str, model: str = PRIMARY_MODEL) -> str:
    """Uses Gemini Function Calling to execute the appropriate system task or returns conversational response.

    1. Sends the user's text to Gemini with task executor tool declarations.
    2. If Gemini selects a function call, executes the corresponding whitelisted task function.
    3. If Gemini responds with plain text, returns that text as normal conversational fallback.
    4. Handles all exceptions gracefully with safe TTS-friendly error messages.

    Args:
        user_text (str): Spoken or typed user command.
        model (str): Target Gemini model identifier.

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

    models_to_try = [model]
    if FALLBACK_MODEL not in models_to_try:
        models_to_try.append(FALLBACK_MODEL)

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
        except Exception as err:
            print(f"[Error: Gemini Action Router] Exception on {target_model}: {err}")

    # Fallback to direct conversational response if function calling endpoint is temporarily unreachable
    fallback_text = generate_response(user_text)
    if fallback_text:
        return fallback_text

    return "Sorry, I am currently having trouble processing your command."


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
