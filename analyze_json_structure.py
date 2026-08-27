import json
import re


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

MAX_CHARS_PER_CHUNK = 50000

FILENAME = "dnd-phandelver-below.pbso-adventures.json"


# ------------------------------------------------------------
# Protected strings
# ------------------------------------------------------------

PROTECTED_PATTERNS = [
    # Foundry UUID references:
    # @UUID[JournalEntry.abc123]{Some Text}
    r"@UUID\[[^\]]+\](?:\{[^}]*\})?",

    # Foundry references:
    # @Reference[reaction]{reactions}
    r"@Reference\[[^\]]+\](?:\{[^}]*\})?",
]


# ------------------------------------------------------------
# Find protected ranges
# ------------------------------------------------------------

def find_protected_ranges(text):
    ranges = []

    for pattern in PROTECTED_PATTERNS:
        for match in re.finditer(pattern, text):
            ranges.append(
                (match.start(), match.end())
            )

    ranges.sort()

    return ranges


# ------------------------------------------------------------
# Protected range check
# ------------------------------------------------------------

def is_inside_protected_range(
        position,
        protected_ranges
):
    for start, end in protected_ranges:

        if start < position < end:
            return True

        if start >= position:
            break

    return False


# ------------------------------------------------------------
# Find sentence boundaries
# ------------------------------------------------------------

def is_sentence_boundary(text, position):
    """
    Returns True if position is immediately after
    a sentence-ending punctuation mark.

    Examples:
        "This is a sentence. |"
        "Really? |"
        "Yes! |"
    """

    if position <= 0:
        return False

    return text[position - 1] in ".!?"


# ------------------------------------------------------------
# Find word boundary
# ------------------------------------------------------------

def is_word_boundary(text, position):
    """
    Returns True if the cut does not split a word.
    """

    if position <= 0 or position >= len(text):
        return True

    return not (
            text[position - 1].isalnum()
            and text[position].isalnum()
    )


# ------------------------------------------------------------
# Find safe cut position
# ------------------------------------------------------------

def find_safe_cut(
        text,
        hard_limit,
        protected_ranges
):
    """
    Find the best safe cut position <= hard_limit.

    Priority:

        1. Protected string
        2. Sentence boundary
        3. Word boundary

    A protected string must never be split.

    If the hard limit falls inside a protected string,
    we search backwards until we leave it.

    Among the remaining possible positions, we prefer
    a sentence boundary over a word boundary.
    """

    # --------------------------------------------------------
    # First pass:
    # Find the latest sentence boundary that is safe.
    # --------------------------------------------------------

    for position in range(
            hard_limit,
            0,
            -1
    ):

        if is_inside_protected_range(
                position,
                protected_ranges
        ):
            continue

        if is_sentence_boundary(
                text,
                position
        ):
            return position

    # --------------------------------------------------------
    # Second pass:
    # No suitable sentence boundary.
    # Find the latest word boundary that is safe.
    # --------------------------------------------------------

    for position in range(
            hard_limit,
            0,
            -1
    ):

        if is_inside_protected_range(
                position,
                protected_ranges
        ):
            continue

        if is_word_boundary(
                text,
                position
        ):
            return position

    # --------------------------------------------------------
    # No safe boundary found
    # --------------------------------------------------------

    return None


# ------------------------------------------------------------
# Create chunks
# ------------------------------------------------------------

def create_chunks(text):

    protected_ranges = find_protected_ranges(text)

    chunks = []

    start = 0

    while start < len(text):

        remaining_length = len(text) - start

        # ----------------------------------------------------
        # Remaining text fits completely
        # ----------------------------------------------------

        if remaining_length <= MAX_CHARS_PER_CHUNK:

            chunks.append(
                text[start:]
            )

            break

        # ----------------------------------------------------
        # Hard maximum
        # ----------------------------------------------------

        hard_limit = (
                start
                + MAX_CHARS_PER_CHUNK
        )

        # ----------------------------------------------------
        # Find safe boundary
        # ----------------------------------------------------

        cut_position = find_safe_cut(
            text,
            hard_limit,
            protected_ranges
        )

        if cut_position is None:

            raise ValueError(
                f"Could not find a safe chunk boundary "
                f"within {MAX_CHARS_PER_CHUNK} characters "
                f"starting at position {start}."
            )

        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        if cut_position <= start:

            raise ValueError(
                f"Unable to create a non-empty chunk "
                f"starting at position {start}."
            )

        # ----------------------------------------------------
        # Create chunk
        # ----------------------------------------------------

        chunks.append(
            text[start:cut_position]
        )

        start = cut_position

    return chunks


# ------------------------------------------------------------
# Load input
# ------------------------------------------------------------

with open(
        f"input/{FILENAME}",
        "r",
        encoding="utf-8"
) as file:

    data = json.load(file)


# ------------------------------------------------------------
# Serialize JSON
# ------------------------------------------------------------

text = json.dumps(
    data,
    ensure_ascii=False,
    indent=2
)


print("=== INPUT ===")
print(f"File: {FILENAME}")
print(f"Characters: {len(text)}")


# ------------------------------------------------------------
# Create chunks
# ------------------------------------------------------------

chunks = create_chunks(text)


# ------------------------------------------------------------
# Report results
# ------------------------------------------------------------

print(
    f"\n=== CHUNKS: {len(chunks)} ==="
)

for index, chunk in enumerate(
        chunks,
        start=1
):

    print(
        f"Chunk {index}: "
        f"{len(chunk)} characters"
    )

    print(f"  END:   {repr(chunk[-100:])}")
    if index < len(chunks):
        print(f"  START: {repr(chunks[index][:100])}")