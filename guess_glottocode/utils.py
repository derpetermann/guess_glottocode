import requests
import io
import zipfile
import pandas as pd
import geopandas as gpd
import configparser


from geopandas import GeoDataFrame
from typing import List, Union, Dict, Any
from pathlib import Path
from platformdirs import user_cache_dir
from shapely.geometry import Point, Polygon, MultiPolygon
from urllib.parse import urljoin
from io import StringIO


APP_NAME = "guess_glottocode"
LOOKUP_URL = "https://cdstar.eva.mpg.de//bitstreams/EAEA0-2198-D710-AA36-0/glottolog_languoid.csv.zip"
LOOKUP_FILENAME_IN_ZIP = "languoid.csv"

GeometryInput = Union[
    tuple[float, float],
    Point,
    Polygon,
    MultiPolygon,
    gpd.GeoSeries
]

def get_lookup_table(force_refresh: bool = False) -> Path:
    """
    Download and cache a lookup table embedded in a ZIP file from a remote URL.

    The function downloads the ZIP file only if the lookup table is not already cached,
    or if `force_refresh` is set to True. The target file inside the ZIP is extracted
    and stored in the appropriate OS-specific cache directory for future reuse.

    Args:
        force_refresh (bool): If True, forces re-downloading and re-extracting the file
            even if a cached version exists

    Returns:
        Path: The local path to the extracted lookup table CSV file.

    Raises:
        FileNotFoundError: If the expected file is not found inside the ZIP archive.
        Requests.HTTPError: If the HTTP request to download the ZIP file fails.
    """

    cache_dir = Path(user_cache_dir(APP_NAME))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "languoid.csv"

    if not cache_file.exists() or force_refresh:
        response = requests.get(LOOKUP_URL)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            if LOOKUP_FILENAME_IN_ZIP not in zf.namelist():
                raise FileNotFoundError(
                    f"'{LOOKUP_FILENAME_IN_ZIP}' not found in the ZIP archive "
                    f"downloaded from: '{LOOKUP_URL}'."
                )

            with zf.open(LOOKUP_FILENAME_IN_ZIP) as source, cache_file.open('wb') as target:
                target.write(source.read())

    return cache_file

def get_glottolog() -> gpd.GeoDataFrame:
    """
    Load and convert Glottolog language data into a GeoDataFrame with point geometries.

    This function reads a cached CSV file containing language metadata and coordinates
    (longitude, latitude), and returns it as a GeoDataFrame with geographic point geometry.

    Returns:
        GeoDataFrame: A GeoDataFrame with language metadata and geographic point geometry.
                      The CRS is set to EPSG:4326 (WGS84).
    """
    lookup_path = get_lookup_table()
    df = pd.read_csv(lookup_path)

    return GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326"
    )


# Finds all glottocodes near the language
def geo_filter_glottocodes(
    language_location: GeometryInput,
    buffer: float,
    level: str
) -> GeoDataFrame:
    """
    Filter Glottolog language entries by geographic proximity and family relationships.

    This function finds Glottolog languages within a given buffer (in kilometers) around a specified
    location. It also includes the parents and children of the nearby languages. Optionally, results
    can be filtered by Glottolog 'level' (dialect, language, family)

    Args:
        language_location (GeometryInput): The target location. Can be:
            - A (longitude, latitude) tuple,
            - A shapely Point, Polygon or MultiPolygon
            - A GeoSeries of Points or Polygons
        buffer (float): Radius in kilometers around the location to search for languages
        level (str): If 'all', return all matching candidates.
                     Otherwise, filter by Glottolog 'level' ('dialect', 'language', 'family')

    Returns:
        GeoDataFrame: A GeoDataFrame of Glottolog entries that match spatially
                      filtered by the specified level (if not 'all').
    """
    language_geometry = process_location(language_location)
    glottolog_geometries = get_glottolog()

    estimated_utm = language_geometry.estimate_utm_crs()

    # Buffer in kilometers (convert to meters)
    buffer_polygon = (
        language_geometry.to_crs(estimated_utm)
        .buffer(distance=buffer * 1000)
        .to_crs(glottolog_geometries.crs)
    )

    # Find nearby languages within buffer
    near = gpd.sjoin(
        glottolog_geometries,
        gpd.GeoDataFrame(geometry=buffer_polygon, crs=glottolog_geometries.crs),
        predicate='within'
    )['id'].tolist()

    # Include children and parents of nearby languages
    children = find_children(near, glottolog_geometries)
    parents = find_parents(near, glottolog_geometries)

    # Combine all candidate IDs and filter
    candidate_ids = { *near, *children, *parents }
    candidates = glottolog_geometries.loc[
        glottolog_geometries['id'].isin(candidate_ids)
    ]

    if level not in {'all', 'language', 'dialect', 'family'}:
        raise ValueError(f"Invalid level: {level}. "
                         f"Must be one of 'all', 'language', 'dialect', 'family'.")

    if level == 'all':
        return candidates
    else:
        return candidates[candidates['level'] == level]

def find_children(candidate_ids: List[Union[str, int]], relatives: pd.DataFrame) -> List[Union[str, int]]:
    """
    Find the child IDs of given candidate languages IDs based on a DataFrame of relationships.

    Args:
        candidate_ids (List[Union[str, int]]): A list of candidate IDs
        relatives (pd.DataFrame): A DataFrame with at least two columns:
            - 'id': Unique identifier for each row (child)
            - 'parent_id': Identifier of the parent

    Returns:
        List[Union[str, int]]: A list of child IDs whose 'parent_id' matches any of the candidate IDs.
    """
    return relatives[relatives['parent_id'].isin(candidate_ids)]['id'].tolist()


def find_parents(candidate_ids: List[Union[str, int]], relatives: pd.DataFrame) -> List[str]:
    """
    Find the parent IDs of given candidate IDs based on a DataFrame of relationships.

    Args:
        candidate_ids (List[Union[str, int]]): A list of candidate IDs
        relatives (pd.DataFrame): A DataFrame with at least two columns:
            - 'id': Unique identifier for each row (child)
            - 'parent_id': Identifier of the parent

    Returns:
        List[str]: A list of parent IDs (as strings) whose 'id' matches any of the candidate child IDs.
                   Only parent IDs of type `str` are included.
    """
    parents = relatives[relatives['id'].isin(candidate_ids)]['parent_id']
    return [p for p in parents if isinstance(p, str)]


def process_location(location: GeometryInput) -> gpd.GeoSeries:
    """
    Normalise various user-provided location formats into a GeoSeries.

    Args:
        location (GeometryInput): Location can be provided as:
            - A (longitude, latitude) tuple
            - A shapely.geometry.Point
            - A shapely.geometry.Polygon
            - A GeoPandas GeoSeries of Points or Polygons

    Returns:
        GeoSeries: A GeoSeries containing the provided geometry.
        """

    if isinstance(location, tuple):
        lon, lat = location
        geom = Point(lon, lat)
        return gpd.GeoSeries([geom], crs="EPSG:4326")

    elif isinstance(location, (Point, Polygon, MultiPolygon)):
        return gpd.GeoSeries([location], crs="EPSG:4326")

    elif isinstance(location, gpd.GeoSeries):
        # Set CRS only if not already set
        return location.set_crs("EPSG:4326", allow_override=True) if location.crs is None else location

    else:
        raise TypeError(
            f"Unsupported location type: {type(location)}. "
            "Expected (lon, lat) tuple, Point, Polygon, or GeoSeries."
        )

def find_ancestors(glottocode: str, relatives: pd.DataFrame) -> List[str]:
    """
    Trace the ancestry of a given language based on Glottocode hierarchy.

    Args:
        glottocode (str): The Glottocode of the language whose ancestors should be found
        relatives (pd.DataFrame): A DataFrame containing 'id' and 'parent_id' columns representing the hierarchy.

    Returns:
        List[str]: A list of Glottocodes representing the ancestry path,
                   ordered from the root ancestor down to the input language.
    """
    ancestors = []
    current_glottocode = glottocode

    while isinstance(current_glottocode, str):
        ancestors.append(current_glottocode)
        match = relatives[relatives['id'] == current_glottocode]
        if match.empty:
            break
        current_glottocode = match['parent_id'].iloc[0]

    ancestors.reverse()
    return ancestors

def build_url(ancestors: List[str], header: str) -> str:
    """
    Construct a URL path to a `md.ini` file based on a list of ancestors.

    Args:
        ancestors (List[str]): A list of ancestor Glottocodes or path segments
        header (str): The base URL

    Returns:
        str: A URL pointing to the `md.ini` file at the constructed path.
    """
    path = '/'.join(ancestors) + '/md.ini'
    return urljoin(header + '/', path)

def parse_ini(resp: str) -> Dict[str, Dict[str, str]]:
    """
    Convert an INI-formatted string to a nested dictionary.

    Args:
        resp (str): The content of an INI file as a string.

    Returns:
        Dict[str, Dict[str, str]]: A dictionary where each key is a section name,
        and the value is a dictionary of key-value pairs from that section.
    """

    ini_file = StringIO(resp)
    config = configparser.ConfigParser(interpolation=None)
    config.read_file(ini_file)

    ini_dict = {
        section: dict(config.items(section))
        for section in config.sections()
    }

    return ini_dict

def extract_altnames(response: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract and clean alternative names from a response dictionary.

    Args:
        response (Dict[str, Any]): A dictionary expected to contain an 'altnames' key
            The value should itself be a dictionary of strings with newline-separated names

    Returns:
        Dict[str, List[str]]: A dictionary where each key maps to a list of cleaned alternative names
                              Empty strings are removed from the lists

    Raises:
        KeyError: If the 'altnames' key is not present in the input dictionary.
    """
    altnames = response.get('altnames', {})
    return {
        key: [v for v in value.split('\n') if v]
        for key, value in altnames.items()
    }

def check_name(language: str, name_glottolog: str, alt_names_glottolog: Dict[str, List[str]]) -> bool:
    """
    Check if a given language name matches either the primary name or any alternative names from Glottolog.

    Args:
        language (str): The language name to check
        name_glottolog (str): The primary Glottolog name
        alt_names_glottolog (Dict[str, List[str]]): A dictionary of alternative names, grouped by source

    Returns:
        bool: True if the language matches the primary or any alternative name; False otherwise.
    """
    norm = lambda s: s.lower().lstrip()

    if norm(name_glottolog) == norm(language):
        return True

    for source in alt_names_glottolog.values():
        for alt in source:
            if norm(alt) == norm(language):
                return True

    return False


def verify_glottocode_guess(language: str, glottocode: str) -> bool:
    """
    Verify whether a guessed Glottocode corresponds to a given language name
    using metadata scraped from Glottolog.

    Args:
        language (str): The name of the language to verify (e.g., "Yuracaré")
        glottocode (str): The guessed Glottocode to verify

    Returns:
        bool: True if the name or one of its alternate names matches the input language.
              False if the Glottocode is invalid or verification fails.
    """
    glottolog_data = get_glottolog()
    url_header = "https://raw.githubusercontent.com/glottolog/glottolog/master/languoids/tree"

    try:
        ancestors = find_ancestors(glottocode, glottolog_data)
        url = build_url(ancestors, url_header)

        response_ini = requests.get(url)
        if response_ini.status_code == 404:
            print(f"Could not open {url}. Glottocode verification failed.")
            return False

        response_dict = parse_ini(response_ini.text)
        name_glottolog = response_dict['core']['name']
        altnames_glottolog = extract_altnames(response_dict)

        return check_name(language, name_glottolog, altnames_glottolog)

    except IndexError as e:
        print(f"[IndexError] {e}. Glottocode verification failed.")
        return False
