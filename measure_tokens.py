from pathlib import Path
from openai import OpenAI


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
LLM_MODEL = "gpt-5.4-mini" #"gpt-5.6-luna"

FILES = [
    "dnd-phandelver-below.pbso-adventures.json",
    "dnd-phandelver-below.pbso-bestiary.json",
    "dnd-phandelver-below.pbso-items.json",
    "dnd-phandelver-below.pbso-player-options.json",
    "dnd-phandelver-below.pbso-player-tables.json",
    "test-entry.json",
]


# ------------------------------------------------------------
# Initialize OpenAI API client
# ------------------------------------------------------------

api_key = Path(
    "local_secret_do_not_commit/openai_api_key.txt"
).read_text(
    encoding="utf-8"
).strip()

client = OpenAI(
    api_key=api_key
)


# ------------------------------------------------------------
# Analyze files
# ------------------------------------------------------------

for filename in FILES:

    input_path = Path("input") / filename

    with input_path.open(
            "r",
            encoding="utf-8"
    ) as file:
        text = file.read()

    result = client.responses.input_tokens.count(
        model=LLM_MODEL,
        input=text
    )

    print(
        f"{filename}: "
        f"{len(text):,} characters, "
        f"{len(text.splitlines()):,} lines, "
        f"{result.input_tokens:,} input tokens"
    )