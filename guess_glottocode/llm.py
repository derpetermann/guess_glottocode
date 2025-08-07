import anthropic
import re
import pandas as pd
import keyring

from typing import Literal
from anthropic.types import MessageParam
from google import genai


def send_task(
    task: str,
    role: str,
    api: Literal["anthropic", "gemini"],
    api_key: str
) -> str:
    """
    Send a task to a specified LLM API and return the model's raw response.

    Args:
        task (str): The prompt to send to the language model
        role (str): The system prompt that defines the assistant's role or behavior
        api (str): The name of the API to use ("anthropic" or "gemini")
        api_key (str): The API key required to authenticate with the service

    Returns:
        str: The text content of the LLM's response

    Raises:
        ValueError: If the specified API name is unsupported
    """
    if api == "anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        messages: list[MessageParam] = [
            {
                "role": "user",
                "content": task
            }
        ]
        response = client.messages.create(
            model="claude-3-opus-20240229",
            system=role,
            temperature=0.0,
            max_tokens=4096,
            messages=messages
        )
        return response.content[0].text

    elif api == "gemini":
        # Google Gemini
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=task
        )
        return re.sub(r'\W+', '', response.text)

    else:
        raise ValueError(f"Unsupported API: {api}")


def sanity_check(glottocode_guess: str, cand: pd.DataFrame) -> bool:
    """
    Check whether a guessed Glottocode is valid.

    Args:
        glottocode_guess (str): The guessed Glottocode (from an LLM or other source)
        cand (pd.DataFrame): A DataFrame of candidate languages, each with an 'id' column

    Returns:
        bool: True if the guessed Glottocode is in the list of candidates or is an empty string (no match found);
              False otherwise.
    """
    return glottocode_guess in cand['id'].values or glottocode_guess == ''


def guess_glottocode(
        language: str,
        candidates: pd.DataFrame,
        api: Literal["anthropic", "gemini"],
) -> str | None:
    """
    Use an LLM API to guess the Glottocode for a given language name.

    The function builds a prompt based on a list of candidate languages and uses a language model
    to identify the most likely Glottolog match. If no good match is found or the result is invalid,
    it returns None.

    Args:
        language (str): The name of the language to identify (e.g., "Yuracaré")
        candidates (pd.DataFrame): A DataFrame with columns:
            - 'name': Language name
            - 'id': Glottocode
        api (str): The name of the LLM API to use, either 'gemini' or 'anthropic'

    Returns:
        str | None: The predicted glottocode as plain text if valid, else None.
    """

    lang = language.strip().capitalize()

    role = (
        "You are an experienced linguist at a prestigious university. "
        "You work very carefully and do not want to make mistakes, as they might harm your reputation."
    )

    # Convert candidate DataFrame to JSON for the prompt
    cand = candidates.loc[:, ['name', 'id']].rename(columns={'id': 'glottocode'}).to_json(orient='records')

    task = (
        f"<candidates> is a JSON file containing information about languages and their glottocodes. "
        f"Each entry in <candidates> has attributes name, which is the name of a language, "
        f"and glottocode, which is a unique identifier for the language published by Glottolog. "
        f"<candidates>{cand}</candidates> "
        f"Find the correct glottocode for the language named {lang} in <candidates>. "
        f"First, search for an exact match for {lang} in the name attribute of <candidates>. "
        f"If no exact match is found, look for alternative spellings for {lang}. "
        f"Then, try to match any alternative spelling to the entries in <candidates>. "
        f"If no suitable match is found, return an empty result. "
        f"Return the Glottocode as plain text without additional text or comments."
    )
    if api not in {'gemini', 'anthropic'}:
        raise ValueError(f"Invalid language model: {api}. "
                         f"Must be either 'gemini' or 'anthropic'")
    else:
        api_key = get_api_key(api)
        response = send_task(task, role, api, api_key)

    if sanity_check(response, candidates):
        return response
    else:
        return None


def get_api_key(api: str) -> str:
    """
    Retrieve or prompt for the API key from the system keyring.

    Args:
        api (str): The name of the API service. Supported values are "anthropic" and "gemini".

    Returns:
        str: The stored or newly provided API key for the given service.
    """
    service_name = f"{api}_guess_glottocode"
    key = keyring.get_password(service_name, "user")

    if not key:
        if api == "anthropic":
            key = input("Enter your Anthropic API key: ").strip()
        elif api == "gemini":
            key = input("Enter your Google Gemini API key: ").strip()
        else:
            raise ValueError(f"Unsupported API service: {api}")

        keyring.set_password(service_name, "user", key)

    return key
