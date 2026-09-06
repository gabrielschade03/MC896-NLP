import re
# Verbos e conectores que indicam achado de exame -> condição
TRIGGERS_INDICATES = re.compile(
    r"\b(showed|revealed|demonstrated|indicated|suggesting|consistent\s+with|confirmed|diagnosed\s+as)\b",
    re.IGNORECASE
)

# Conectores que indicam tratamento para uma condição
TRIGGERS_TREATS = re.compile(
    r"\b(treated\s+with|started\s+on|initiated\s+for|prescribed\s+for|managed\s+with|for\s+the\s+treatment\s+of|therapy\s+for|received\s+for|for)\b",
    re.IGNORECASE
)

# Padrões clássicos de negação clínica (NegEx simplificado)
NEGATION_PATTERNS = re.compile(
    r"\b(no\s+evidence\s+of|no\s+signs?\s+of|without|denies|denied|negative\s+for|ruled\s+out|no\s+apparent|free\s+of)\b",
    re.IGNORECASE
)