"""Module for searching Wikipedia and retrieving short summaries."""

import wikipedia

# Set browser User-Agent to satisfy Wikipedia MediaWiki API policy
wikipedia.set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) NexusVoiceAssistant/1.0")


def search_wikipedia(query: str, sentences: int = 2) -> str:
    """Searches Wikipedia for a topic query and returns a short summary.

    Args:
        query (str): The search topic or term.
        sentences (int): Number of summary sentences to return (default 2).

    Returns:
        str: A short summary of the Wikipedia page, or a fallback message if an error occurs.
    """
    try:
        # Fetch a short summary of the topic from Wikipedia
        summary = wikipedia.summary(query, sentences=sentences, auto_suggest=False)
        return summary

    except wikipedia.exceptions.DisambiguationError as err:
        # Disambiguation error happens when a search term points to multiple articles (e.g. 'Mercury')
        print(f"[Wikipedia Search] Multiple matching pages found for '{query}'.")
        return f"There are multiple topics matching '{query}'. Please be more specific."

    except wikipedia.exceptions.PageError:
        # Page error happens when no Wikipedia page matches the search topic
        print(f"[Wikipedia Search] No page found for topic: '{query}'.")
        return f"Sorry, I couldn't find a Wikipedia page for '{query}'."

    except Exception as err:
        # Unexpected error handling (e.g. network failure)
        print(f"[Wikipedia Search] Unexpected error during search: {err}")
        return "Sorry, I encountered an error while searching Wikipedia."


if __name__ == "__main__":
    test_query = "Alan Turing"
    print(f"Searching Wikipedia for: '{test_query}'...\n")
    result = search_wikipedia(test_query)
    print("Result:")
    print(result)
