from pathlib import Path
from openai import OpenAI

api_key = Path(
    "local_secret_do_not_commit/openai_api_key.txt"
).read_text(encoding="utf-8").strip()

client = OpenAI(api_key=api_key)

with open(
        "input/dnd-phandelver-below.pbso-adventures.json",
        "r",
        encoding="utf-8"
) as file:
    text = file.read()

print(f"Characters: {len(text):,}")
print(f"Lines:      {len(text.splitlines()):,}")

result = client.responses.input_tokens.count(
    model="gpt-5.4-mini",
    input=text
)

print(f"Input tokens: {result.input_tokens:,}")