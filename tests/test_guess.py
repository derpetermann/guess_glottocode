
from guess_glottocode.utils import geo_filter_glottocodes, verify_glottocode_guess
import guess_glottocode.wikipedia as wikipedia
import guess_glottocode.llm as llm
import geopandas as gpd

url = "https://r2.datahub.io/clvyjaryy0000la0cxieg4o8o/main/raw/data/countries.geojson"
country_polygons = gpd.read_file(url)
france = country_polygons.query("name == 'France'").geometry

language = "French"
glottocode_wikipedia = wikipedia.guess_glottocode(language)

candidate_glottocodes = geo_filter_glottocodes(language_location = france,
                                               buffer = 500,
                                               level = "language")

glottocode_gemini = llm.guess_glottocode(language = language,
                                         candidates=candidate_glottocodes,
                                         api="gemini")

glottocode_anthropic = llm.guess_glottocode(language = language,
                                            candidates=candidate_glottocodes,
                                            api = "anthropic")

verify = verify_glottocode_guess(language, glottocode_gemini)
