"""Expressões regulares para valores e referências temporais."""

import re


FLAGS = re.IGNORECASE | re.VERBOSE

NUMBER_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|"
    "eleven|twelve"
)
NUMBER = rf"(?:\d+(?:[.,]\d+)?|{NUMBER_WORDS})"
TIME_UNIT = r"(?:minutes?|hours?|days?|weeks?|months?|years?)"
MONTH = (
    r"(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)"
)


DOSE_PATTERN = re.compile(
    r"""
    (?<![\w.])
    (?P<value>\d+(?:[.,]\d+)?)
    \s*
    (?P<unit>mcg|µg|mg|g|mL)
    (?P<rate>(?:\s*/\s*(?:kg|day|d|hour|h|min)){0,2})
    (?!\s*/\s*(?:dL|L))
    \b
    """,
    FLAGS,
)


MEASUREMENT_PATTERN = re.compile(
    r"""
    (?<![\w.])
    (?P<value>\d+(?:[.,]\d+)?)
    \s*
    (?P<unit>
        mg/dL|g/dL|mmol/L|ng/mL|IU/L|U/L|mL/min(?:ute)?
        |mmHg|beats\s*(?:per|/)\s*min(?:ute)?|bpm|°\s*C|C
    )
    \b
    """,
    FLAGS,
)


RELATIVE_TIME_PATTERN = re.compile(
    rf"""
    \b
    (?:
        (?P<quantity>{NUMBER})
        \s+
        (?P<unit>{TIME_UNIT})
        \s+
        (?P<direction>later|after|before|prior\s+to)
        (?:\s+(?P<reference>admission|surgery|operation|diagnosis|treatment|discharge))?
        |
        (?P<sequence>the\s+(?:following|next)\s+day)
    )
    \b
    """,
    FLAGS,
)


DURATION_PATTERN = re.compile(
    rf"""
    \b
    (?P<prefix>for|during|over(?:\s+a\s+period\s+of)?)
    \s+
    (?P<quantity>{NUMBER})
    \s+
    (?P<unit>{TIME_UNIT})
    (?!\s+(?:later|after|before|prior\s+to))
    \b
    """,
    FLAGS,
)


HISTORY_DURATION_PATTERN = re.compile(
    rf"""
    \b
    (?:a\s+)?
    (?P<quantity>{NUMBER})
    [ -]
    (?P<unit>minute|hour|day|week|month|year)
    (?:-|\s+)
    history
    \b
    """,
    FLAGS,
)


ABSOLUTE_DATE_PATTERN = re.compile(
    rf"""
    \b
    (?:
        {MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}
        |
        \d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH}\s+\d{{4}}
    )
    \b
    """,
    FLAGS,
)


PATTERNS = {
    "dose": DOSE_PATTERN,
    "measurement": MEASUREMENT_PATTERN,
    "relative_time": RELATIVE_TIME_PATTERN,
    "duration": DURATION_PATTERN,
    "history_duration": HISTORY_DURATION_PATTERN,
    "absolute_date": ABSOLUTE_DATE_PATTERN,
}


def find_patterns(text):
    """Devolve as estruturas encontradas, seus campos e posições no texto."""
    results = []

    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            result = {
                "kind": kind,
                "text": match.group(0),
                "start": match.start(),
                "end": match.end(),
            }
            result.update({
                name: value
                for name, value in match.groupdict().items()
                if value not in (None, "")
            })
            results.append(result)

    return sorted(results, key=lambda result: (result["start"], result["end"]))
