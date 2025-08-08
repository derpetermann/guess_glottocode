import wptools
from typing import List, Dict, Any
from mediawiki import MediaWiki

def query_wiki(language: str) -> List[Dict[str, str]]:
    """
    Query Wikipedia for pages related to a natural language.

    Args:
        language (str): The name of a natural language (e.g., "French", "Yuracaré").

    Returns:
        List[Dict[str, str]]: A list of dictionaries, each containing:
            - 'name': the original language string,
            - 'title': the Wikipedia page title,
            - 'relevance': the result index (lower is more relevant).
        Results are sorted by their original relevance from Wikipedia.
    """
    pages = []
    query_results = MediaWiki().search(f"{language} language")

    for i, q in enumerate(query_results):
        title_lower = q.lower()

        # Skip programming languages
        if "programming language" in title_lower:
            continue

        # Keep entries clearly about a language, but not plurals like "languages of"
        if "language" in title_lower and "languages" not in title_lower:
            pages.append({
                "name": language,
                "title": q,
                "relevance": i
            })

    return sorted(pages, key=lambda d: d["relevance"])


def retrieve_infobox(sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Retrieve info boxes from a list of Wikipedia pages using wptools.

    Each input dictionary must contain a 'title' key, which is used to query the page.
    Pages without info boxes or that fail to parse are excluded from the final result.

    Args:
        sites (List[Dict[str, Any]]): A list of page metadata dictionaries, each with a 'title' key.

    Returns:
        List[Dict[str, Any]]: A filtered list of dictionaries, each augmented with an 'infobox' key
                              (a dictionary of infobox data).
    """
    for s in sites:
        try:
            page = wptools.page(s["title"]).get_parse(show=False)
            s["infobox"] = page.data.get("infobox", {})
        except Exception as e:
            s["infobox"] = {}
            print(f"No infobox for '{s['title']}': {e}")
    return [s for s in sites if s["infobox"]]


def parse_infobox(sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter pages that contain Glottocode-related data in their infobox.

    For each site, this function checks whether any key in the infobox contains
    the substring "glotto" (case-insensitive). If so, it sets the key 'glotto_site' to True.
    Only pages with a matching infobox key are returned.

    Args:
        sites (List[Dict[str, Any]]): A list of page dictionaries with 'infobox' keys.

    Returns:
        List[Dict[str, Any]]: Filtered list of pages where the infobox contains a Glottocode key.
                              Each returned dictionary includes a 'glotto_site' boolean key.
    """
    for s in sites:
        s["glotto_site"] = any("glotto" in key.lower() for key in s.get("infobox", {}).keys())

    return [s for s in sites if s["glotto_site"]]


def parse_glottocode(sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract glottocode entries from the info boxes of Wikipedia pages.

    This function searches each infobox for keys that start with "glotto", and collects
    their values. Keys named exactly "glotto" or "glotto1" are marked as primary glottocodes.

    Args:
        sites (List[Dict[str, Any]]): List of page dictionaries that contain an 'infobox' key.

    Returns:
        List[Dict[str, Any]]: Filtered list of pages, each with an added 'glottocode' key
                              containing a list of dicts with:
                                - 'code' (str): The extracted glottocode.
                                - 'primary' (bool): Whether the code is marked as primary.
    """
    for s in sites:
        glottocodes = []
        for key, value in s.get("infobox", {}).items():
            if key.startswith("glotto") and value:
                is_primary = key in {"glotto", "glotto1"}
                glottocodes.append({
                    "code": value,
                    "primary": is_primary
                })
        s["glottocode"] = glottocodes

    return [s for s in sites if s.get("glottocode")]


def get_most_relevant_glottocode(
    sites: List[Dict[str, Any]],
    only_primary: bool = True
) -> str | None:
    """
    Extract glottocode from the most relevant Wikipedia page. If no Glottocode is found,
    this function returns None.

    Args:
        sites (List[Dict[str, Any]]): A list of Wikipedia page dictionaries, each
            expected to contain a 'glottocode' key with a list of dicts, where each
            dict has a 'code' (str) and 'primary' (bool).
        only_primary (bool): If True, include only glottocodes marked as primary.

    Returns:
        List[str]: A list of glottocode strings from the top-k relevant pages.
    """
    for site in sites:
        for code_info in site.get("glottocode", []):
            if code_info["primary"] or not only_primary:
                return code_info["code"]
    return None

def guess_glottocode(
    language: str,
    only_primary: bool = True
) -> str | None:
    """
    Guess glottocode(s) for a language using Wikipedia data.

    This function performs a multistep process:
    1. Query Wikipedia pages related to the language.
    2. Retrieve info boxes from these pages.
    3. Filter pages containing glottocode-related info.
    4. Extract glottocodes from those info boxes.
    5. Return glottocodes from the most relevant page.

    Args:
        language (str): Name of the language to query.
        only_primary (bool): Whether to include only primary glottocodes.

    Returns:
        str: List of guessed glottocodes, possibly empty if none found.
    """
    language = language.strip().capitalize()

    wiki_sites = query_wiki(language)
    if not wiki_sites:
        return []

    sites_with_infobox = retrieve_infobox(wiki_sites)
    if not sites_with_infobox:
        return []

    sites_with_glottocode_info = parse_infobox(sites_with_infobox)
    if not sites_with_glottocode_info:
        return []

    sites_with_glottocode = parse_glottocode(sites_with_glottocode_info)
    if not sites_with_glottocode:
        return []

    return get_most_relevant_glottocode(
        sites_with_glottocode,
        only_primary=only_primary
    )
