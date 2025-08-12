# guess_glottocode

Guess the Glottocode* for a language using either a Wikipedia query or a large language model.

\* Glottocodes are unique identifiers for languages maintained by [Glottolog](https://glottolog.org).

## Features

- Query Wikipedia to find the Glottocode of a language.
- Use advanced large language models (Gemini, Anthropic) for enhanced guesses.


## Installation

You can install the latest version directly from GitHub:

```bash
pip install git+https://github.com/derpetermann/guess_glottocode.git
```

Or install via PyPI (coming soon):
```bash
pip install guess_glottocode
```

## Useful references:

- [Glottolog](https://glottolog.org) - Open language catalog, maintains Glottocodes  
- [Google Gemini](https://aistudio.google.com/apikey) - API key setup for Gemini  
- [Anthropic](https://console.anthropic.com/settings/keys) - API key setup for Anthropic  
- [GeoPandas Documentation](https://geopandas.org/en/stable/) - Geospatial data handling in Python


## API Keys 

When using the `guess_glottocode` package to find the Glottocode of a language via a large language model (LLM), the package sends an API request to an LLM provider. Currently, supported providers are Google Gemini and Anthropic. To use these services, you must first create an API key for one of them. 

For Google Gemini, you can create an API key at https://aistudio.google.com/apikey. You will need a Google account and must be logged in.
For Anthropic, you can create an API key at https://console.anthropic.com/settings/keys. You will need to sign up for and log in to an Anthropic account. Moderate use of the package shouldn't incur third-party API costs, but heavier usage might.

The first time you call the `llm.guess_glottocode` function to launch a Gemini or Anthropic API request, the package will prompt you to enter your API key. The key is then stored securely on your local machine using the `keyring` package, so you won't need to enter it again in future sessions.

When using a Wikipedia query instead of an LLM, no API key is required.

## Package Structure and Imports

Here are the main modules:

- `guess_glottocode.wikipedia` - Wikipedia queries
- `guess_glottocode.llm` - Guessing Glottocodes with large language models
- `guess_glottocode.utils` - Utility functions like verification and geographic filters

Typical imports will use:

``` python
import guess_glottocode.wikipedia as wikipedia
import guess_glottocode.llm as llm
from  guess_glottocode.utils import geo_filter_glottocodes
from guess_glottocode.utils import verify_glottocode_guess

```

## Usage

This package provides functions to guess the Glottocode of a language either by querying Wikipedia or by sending a prompt to a large language model (LLM) and processing the response.

### Querying Wikipedia 

Find the Glottocode of French using a Wikipedia query:

```python
import guess_glottocode.wikipedia as wikipedia
glottocode_wikipedia = wikipedia.guess_glottocode(language="French")
```

### Guessing Glottocodes with large language models

We found that current LLMs still struggle to correctly identify the Glottocode for a language without additional context, and they can sometimes hallucinate incorrect results. A more reliable approach is to first generate a set of candidate Glottocodes based on a geographic filter, and then prompt the LLM to filter and select the best match from those candidates.


```python
import guess_glottocode.llm as llm
from  guess_glottocode.utils import geo_filter_glottocodes

candidate_glottocodes = geo_filter_glottocodes(language_location=(2.5, 48.4),
                                               buffer=500,
                                               level="language")

glottocode_gemini = llm.guess_glottocode(language="French",
                                         candidates=candidate_glottocodes,
                                         api="gemini")
```

The `geo_filter_glottocodes` function creates a buffer — 500 km in this example — around the given language location, in this example specified as a pair of longitude and latitude coordinates. It then filters all Glottocodes to find suitable candidates, here focusing on the language level while excluding Glottocodes of dialects or language families. After that, `llm.guess_glottocode` sends a prompt to an API — Gemini in this case — to select the best matching Glottocode from the candidate list.

### Suitable geographic filters 

The geographic filter is key to finding a matching Glottocode. If the filter is too broad, it will return too many candidate Glottocodes, leading to a long prompt and potentially high token costs and suboptimal results. If the filter is too narrow, it may return too few candidates or even exclude the relevant one, resulting in a wrong or empty LLM guess. The `geo_filter_glottocodes` function accepts as `language_location` a (longitude, latitude) tuple, a Shapely Point, Polygon, or MultiPolygon, or a geopandas GeoSeries of Points, Polygons or MultiPolygons to create the geometry for the geographic filter. 

If you don't have a suitable geometry for the filter, you can easily create one using publicly available geometries and load it with `GeoPandas`.


```python
import geopandas as gpd
url = "https://r2.datahub.io/clvyjaryy0000la0cxieg4o8o/main/raw/data/countries.geojson"
country_polygons = gpd.read_file(url)
france = country_polygons.query("name == 'France'").geometry

candidate_glottocodes = geo_filter_glottocodes(language_location=france,
                                               buffer=100,
                                               level="language")

glottocode_anthropic = llm.guess_glottocode(language=language,
                                            candidates=candidate_glottocodes,
                                            api="anthropic")
```  


The buffer of 100 km ensures that potential differences in coverage won't exclude relevant candidates. You can restrict the candidate Glottocodes by setting level to 'language', which only returns Glottocodes marked as languages in Glottolog, 'dialect', 'family', or 'all'.

### Verify the Glottocode

Finally, you can verify the Glottocode match. Each Glottocode is linked to a GitHub page containing the language's primary name and any alternative names. The function queries that page and checks if your language name appears as the primary name or among the alternatives. If it does, the check returns `True`; otherwise, it returns `False`.

```python
from guess_glottocode.utils import verify_glottocode_guess
verify = verify_glottocode_guess(language, glottocode_gemini)
```

## Requirements
- Python 3.12+
- Dependencies listed in pyproject.toml

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Peter Ranacher - peter.ranacher@gmail.com
