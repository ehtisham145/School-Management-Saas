"""Rules for tests made from a PDF: limits, ready patterns, paper themes, and the checks
every AI question must pass before a teacher sees it. No database access here."""

import math
import re
import unicodedata
from datetime import timedelta
from decimal import Decimal

MCQ, TRUE_FALSE, FILL_BLANK, SHORT_ANSWER = "mcq", "true_false", "fill_blank", "short_answer"
KINDS = (MCQ, TRUE_FALSE, FILL_BLANK, SHORT_ANSWER)
DIFFICULTIES = ("easy", "medium", "hard")

MAX_PDF_BYTES = 8 * 1024 * 1024  # The server takes 10 MB per request; this leaves room.
MAX_PDF_PAGES = 50
MAX_SECTIONS = 6
MAX_SECTION_QUESTIONS = 30
MAX_AI_QUESTIONS = 50
MAX_EXAM_QUESTIONS = 100
MAX_PATTERNS = 30
MAX_REGENERATIONS = 5
MIN_MARKS = Decimal("0.25")
MAX_MARKS = Decimal("100")
DRAFT_LIFETIME = timedelta(hours=24)
# A draft still "being written" after this is treated as lost (a worker restart, say).
PENDING_TIMEOUT = timedelta(minutes=15)
MIN_CONTENT_CHARS = 300
MAX_CONTENT_CHARS = 40_000
MAX_PARALLEL_CALLS = 4

PRESETS = [
    {
        "key": "quick_quiz",
        "sections": [{"kind": MCQ, "count": 10, "marks": "1", "difficulty": "medium"}],
    },
    {
        "key": "mixed",
        "sections": [
            {"kind": MCQ, "count": 10, "marks": "1", "difficulty": "medium"},
            {"kind": TRUE_FALSE, "count": 5, "marks": "1", "difficulty": "easy"},
            {"kind": FILL_BLANK, "count": 5, "marks": "1", "difficulty": "medium"},
        ],
    },
    {
        "key": "exam",
        "sections": [
            {"kind": MCQ, "count": 15, "marks": "1", "difficulty": "medium"},
            {"kind": SHORT_ANSWER, "count": 5, "marks": "3", "difficulty": "hard"},
        ],
    },
]

# Print colors for the paper only. The app's own look comes from the design tokens.
THEMES = {
    "navy": {"accent": "#0F1D31", "soft": "#E8EDF5"},
    "orange": {"accent": "#C2550C", "soft": "#FEF0E5"},
    "green": {"accent": "#166534", "soft": "#DCFCE7"},
    "teal": {"accent": "#0F766E", "soft": "#CCFBF1"},
    "purple": {"accent": "#5B21B6", "soft": "#EDE9FE"},
    "crimson": {"accent": "#9F1239", "soft": "#FFE4E6"},
    "gray": {"accent": "#334155", "soft": "#F1F5F9"},
}
FONT_SIZES = {"small": 11, "normal": 12, "large": 14}
DEFAULT_THEME = {"color": "navy", "font_size": "normal", "columns": 1, "name_line": True}

BANNED_OPTIONS = {
    "all of the above",
    "none of the above",
    "both a and b",
    "جميع ما سبق",
    "كل ما سبق",
    "لا شيء مما سبق",
    "جميع الاجابات صحيحه",
}
BLANK = "_____"
UNDERSCORES = re.compile(r"_{3,}")
TRUE_WORDS = {"true", "صح", "صحيح", "صواب"}
FALSE_WORDS = {"false", "خطأ", "خطا", "خاطئ"}
# Arabic short vowels and Quranic marks, and the tatweel stretch.
ARABIC_MARKS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
ARABIC_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})
NOT_WORD = re.compile(r"[^\w]+")
MIN_QUOTE_WORDS = 4
QUOTE_WINDOW_SHARE = 0.6


def total_questions(sections):
    return sum(section["count"] for section in sections)


# --- The text sent to the AI


def selected_pages(pages, page_from, page_to):
    """[(page number, text)] for the chosen range, leaving out pages with no text."""
    return [
        (number, text)
        for number, text in enumerate(pages[page_from - 1 : page_to], start=page_from)
        if text.strip()
    ]


def content_length(selected):
    return sum(len(text) for _, text in selected)


def content_for_ai(selected):
    """The pages, each marked with its number, cut evenly to fit the size limit."""
    if not selected:
        return ""
    budget = MAX_CONTENT_CHARS // len(selected)
    return "\n\n".join(f"[Page {number}]\n{text[:budget]}" for number, text in selected)


def assign_topics(topics, sections):
    """Shares the topics between the sections, so each one covers a different part."""
    groups = [[] for _ in sections]
    for index, topic in enumerate(topics):
        groups[index % len(sections)].append(topic)
    return groups


# --- Checking what the AI wrote


def normalize(text):
    """For comparing text: no case, Arabic marks, letter variants or punctuation."""
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    text = ARABIC_MARKS.sub("", text).translate(ARABIC_LETTERS)
    return " ".join(NOT_WORD.sub(" ", text).split())


def find_quote(quote, normalized_pages):
    """The page the quote comes from, or None when it isn't in the material.

    The AI is told to copy the words exactly, but may change one or two. So a run of most
    of the quote's words, in order, is enough."""
    words = normalize(quote).split()
    if len(words) < MIN_QUOTE_WORDS:
        return None
    size = (
        len(words)
        if len(words) <= MIN_QUOTE_WORDS
        else max(MIN_QUOTE_WORDS, math.ceil(len(words) * QUOTE_WINDOW_SHARE))
    )
    windows = [" ".join(words[start : start + size]) for start in range(len(words) - size + 1)]
    for number, text in normalized_pages:
        padded = f" {text} "
        if any(f" {window} " in padded for window in windows):
            return number
    return None


def _clip(value, limit):
    return str(value or "").strip()[:limit]


def clean_question(raw, kind):
    """A question in the saved shape, or None when it breaks a rule."""
    text = _clip(raw.get("text"), 1000)
    if not text:
        return None
    question = {
        "kind": kind,
        "text": text,
        "options": [],
        "correct_option": None,
        "answer": "",
        "explanation": _clip(raw.get("explanation"), 1000),
    }

    if kind == MCQ:
        options = [_clip(option, 300) for option in raw.get("options") or []]
        correct = raw.get("correct_option")
        normalized = [normalize(option) for option in options]
        if (
            not 3 <= len(options) <= 6
            or not all(normalized)
            or len(set(normalized)) != len(options)
            or any(option in BANNED_OPTIONS for option in normalized)
            or not isinstance(correct, int)
            or isinstance(correct, bool)
            or not 0 <= correct < len(options)
        ):
            return None
        question.update(options=options, correct_option=correct)
    elif kind == TRUE_FALSE:
        answer = normalize(raw.get("answer"))
        if answer in TRUE_WORDS:
            question["answer"] = "true"
        elif answer in FALSE_WORDS:
            question["answer"] = "false"
        else:
            return None
    elif kind == FILL_BLANK:
        text = UNDERSCORES.sub(BLANK, text)
        answer = _clip(raw.get("answer"), 200)
        if text.count(BLANK) != 1 or not answer:
            return None
        question.update(text=text, answer=answer)
    else:
        answer = _clip(raw.get("answer"), 1000)
        if not answer:
            return None
        question["answer"] = answer
    return question


def build_questions(sections, replies, selected):
    """Turns each section's AI reply into checked questions, in section order.

    A question is dropped when it breaks a rule, can't be found in the material, or repeats
    another one. Each section keeps at most the number asked for."""
    normalized_pages = [(number, normalize(text)) for number, text in selected]
    seen = set()
    questions = []
    for section, reply in zip(sections, replies, strict=True):
        kept = 0
        for raw in reply or []:
            if kept == section["count"]:
                break
            question = clean_question(raw, section["kind"])
            if question is None:
                continue
            page = find_quote(raw.get("quote", ""), normalized_pages)
            key = normalize(question["text"])
            if page is None or key in seen:
                continue
            seen.add(key)
            kept += 1
            questions.append(
                {
                    **question,
                    "marks": str(section["marks"]),
                    "difficulty": section["difficulty"],
                    "source_page": page,
                }
            )
    return questions


# --- How numbers look on paper


def format_marks(value):
    """Decimal("1.50") as "1.5", Decimal("2.00") as "2"."""
    return f"{Decimal(value).normalize():f}"
