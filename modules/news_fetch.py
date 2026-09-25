"""Module for fetching top news headlines using NewsAPI and requests."""

import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env
load_dotenv()


def fetch_top_news(limit: int = 3, country: str = "us") -> str:
    """Fetches the top news headlines using the NewsAPI service.

    Args:
        limit (int): Maximum number of headlines to return (default is 3).
        country (str): 2-letter ISO country code (default is 'us').

    Returns:
        str: Formatted string containing the top news headlines, or a fallback error message.
    """
    api_key = os.getenv("NEWSAPI_KEY")

    if not api_key:
        print("[News Fetch] Missing NEWSAPI_KEY in .env file.")
        return "Sorry, news service is unavailable because the News API key is missing."

    url = f"https://newsapi.org/v2/top-headlines?country={country}&pageSize={limit}&apiKey={api_key}"

    try:
        response = requests.get(url, timeout=10)

        # Handle specific HTTP error status codes
        if response.status_code == 401:
            print("[News Fetch] Invalid NewsAPI key (HTTP 401).")
            return "Sorry, unable to fetch news due to an invalid API key."
        elif response.status_code == 429:
            print("[News Fetch] Rate limit exceeded (HTTP 429).")
            return "Sorry, news rate limit reached. Please try again later."
        elif response.status_code != 200:
            print(f"[News Fetch] NewsAPI returned error HTTP status code {response.status_code}.")
            return "Sorry, I couldn't retrieve the news headlines right now."

        data = response.json()
        articles = data.get("articles", [])

        if not articles:
            return "No top headlines found at the moment."

        headlines = []
        for i, article in enumerate(articles[:limit], 1):
            title = article.get("title", "No Title")
            headlines.append(f"{i}. {title}")

        return "\n".join(headlines)

    except requests.exceptions.Timeout:
        print("[News Fetch] Request timed out.")
        return "Sorry, the news request timed out. Please check your network connection."
    except requests.exceptions.RequestException as err:
        print(f"[News Fetch] Network request failed: {err}")
        return "Sorry, I couldn't connect to the news service. Please check your internet."
    except Exception as err:
        print(f"[News Fetch] Unexpected error fetching news: {err}")
        return "Sorry, an unexpected error occurred while fetching news."


if __name__ == "__main__":
    print("Fetching top 3 news headlines...\n")
    news_result = fetch_top_news(limit=3)
    print("Headlines:")
    print(news_result)
