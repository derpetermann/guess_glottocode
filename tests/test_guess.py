
from guess_glottocode.utils import geo_filter_glottocodes, verify_glottocode_guess
import guess_glottocode.wikipedia as wikipedia
import guess_glottocode.llm as llm
import geopandas as gpd

url = "https://r2.datahub.io/clvyjaryy0000la0cxieg4o8o/main/raw/data/countries.geojson"
country_polygons = gpd.read_file(url)
france = country_polygons.query("name == 'France'")

language = "French"
glottocode_wikipedia = wikipedia.guess_glottocode(language)[0]


candidate_glottocodes = geo_filter_glottocodes(language_location = france.geometry,
                                               buffer = 500,
                                               level = "language")

glottocode_gemini = llm.guess_glottocode(language = language,
                                         candidates=candidate_glottocodes,
                                         api="gemini")

glottocode_anthropic = llm.guess_glottocode(language = language,
                                            candidates=candidate_glottocodes,
                                            api = "anthropic")

verify = verify_glottocode_guess(language, glottocode_gemini)

# More description for obtaining keys
# Retrieve polygon of
# The prompt to the large language model requires a suitable geographic filter to work appropriately.
# if the filter is too coarse too many candidate glottocodes. Long prompt, might invke costs from the LLM API
# if the filter is too narrow too few candidates without the relevant one. The query might be empty.

# Write a brief how too for James
# test package on different venv
# Readme file
# Write Robert about using their
# Suppress mediawiki output
# Media WIKI restrict to first hit, pack [0] into function

