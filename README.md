# guess_glottocode

Guess the Glottocode for a language name using either a Wikipedia query or large language models provided by Gemini or Anthropic.

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

## Usage
```python
from guess_glottocode.utils import geo_filter_glottocodes, verify_glottocode_guess

import guess_glottocode.wikipedia as wikipedia
import guess_glottocode.llm as llm

language = "French"
# Scrape Wikipedia to guess the Glottocode
glottocode_wikipedia = wikipedia.guess_glottocode(language)[0]

# Guess the Glottocode leveraging Gemini's / Anthropic's large language model
# First create a geographic buffer
candidate_glottocodes = geo_filter_glottocodes(language_location = (2.5, 48.4),
                                               buffer = 500,
                                               level = "language")

glottocode_gemini = llm.guess_glottocode(language = language,
                                         candidates=candidate_glottocodes,
                                         api="gemini")

glottocode_anthropic = llm.guess_glottocode(language = language,
                                            candidates=candidate_glottocodes,
                                            api = "anthropic")
# Verify the Glottocode
verify = verify_glottocode_guess(language, glottocode_gemini)
```
## Requirements
- Python 3.12+
- Dependencies listed in pyproject.toml

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Peter Ranacher — peter.ranacher@gmail.com
