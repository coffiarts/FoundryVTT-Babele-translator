import json
import re


def protect_foundry_syntax(text):
    protected = {}

    def replace(match):
        placeholder = f"@@FOUNDRY_{len(protected):03d}@@"
        protected[placeholder] = match.group(0)
        return placeholder

    # Foundry @UUID[...] und @Embed[...] schützen
    text = re.sub(r'@(UUID|Embed)\[[^\]]*\]', replace, text)

    # Foundry Inline-Rolls / Checks / Saves schützen
    text = re.sub(r'\[\[[^\]]*\]\]', replace, text)

    return text, protected


with open("input/test-entry.json", "r", encoding="utf-8") as file:
    data = json.load(file)

original_text = data["Hooked Stones"]["text"]

protected_text, protected = protect_foundry_syntax(original_text)

print("=== GESCHÜTZTER TEXT ===")
print(protected_text)

print("\n=== GESCHÜTZTE ELEMENTE ===")
for placeholder, original in protected.items():
    print(f"{placeholder} -> {original}")

def restore_foundry_syntax(text, protected):
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)
    return text

restored_text = restore_foundry_syntax(protected_text, protected)

print("\n=== ROUNDTRIP ===")
print(restored_text == original_text)