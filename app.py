import json
import os
import random
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Pattern

from flask import Flask, jsonify, render_template, request, session

APP_SECRET = os.environ.get("NOTYOURBUDDY_SECRET", os.urandom(24))

app = Flask(__name__)
app.secret_key = APP_SECRET

LEXICON_PATH = os.path.join(os.path.dirname(__file__), "banter_words.json")


@dataclass
class WordEntry:
    term: str
    rank: int
    normalized: str


UNICODE_NORMALIZERS = str.maketrans({
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "‑": "-",
    "‒": "-",
})


def normalize_term(term: str) -> str:
    ascii_term = term.translate(UNICODE_NORMALIZERS)
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_term.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def append_score_suffix(message: str, score: int) -> str:
    base = message.strip()
    if not base:
        base = "Ok."
    if base[-1] not in ".!?":
        base = f"{base}."
    return f"{base} Score: {score}."


def load_lexicon(path: str) -> List[WordEntry]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    entries = []
    for item in payload.get("words", []):
        term = item["term"].strip()
        rank = int(item.get("rank", 0))
        entries.append(WordEntry(term=term, rank=rank, normalized=normalize_term(term)))
    entries.sort(key=lambda entry: entry.rank)
    return entries


LEXICON: List[WordEntry] = load_lexicon(LEXICON_PATH)
LEXICON_LOOKUP: Dict[str, WordEntry] = {entry.normalized: entry for entry in LEXICON}

SESSION_STATE: Dict[str, Dict[str, object]] = {}

HIDDEN_COMMANDS = {"::list", "/list", "/words", "/ranked", "list please", "show list"}

FOLLOWUP_PATTERNS: List[Pattern[str]] = [
    re.compile(r"^\s*i\s*am\s+not\s+(?:your|yo|ya|ur)\s+(?P<body>[\w'\- ,]+?)\s*[.!?]*$", re.IGNORECASE),
    re.compile(r"^\s*i[' ]?m\s+not\s+(?:your|yo|ya|ur)\s+(?P<body>[\w'\- ,]+?)\s*[.!?]*$", re.IGNORECASE),
    re.compile(r"^\s*im\s+not\s+(?:your|yo|ya|ur)\s+(?P<body>[\w'\- ,]+?)\s*[.!?]*$", re.IGNORECASE),
    re.compile(r"^\s*not\s+(?:your|yo|ya|ur)\s+(?P<body>[\w'\- ,]+?)\s*[.!?]*$", re.IGNORECASE),
]

WORD_FINDER = re.compile(r"[A-Za-z0-9'\-]+")


def initial_state() -> Dict[str, object]:
    return {
        "used": set(),
        "bot_used": set(),
        "score": 0,
        "last_bot_word": None,
        "last_bot_display": None,
    }


def get_state() -> Dict[str, object]:
    state_id = session.get("state_id")
    if not state_id:
        state_id = uuid.uuid4().hex
        session["state_id"] = state_id
    state = SESSION_STATE.setdefault(state_id, initial_state())
    # ensure sets exist (for reloader)
    if not isinstance(state.get("used"), set):
        state["used"] = set(state.get("used", []))
    if not isinstance(state.get("bot_used"), set):
        state["bot_used"] = set(state.get("bot_used", []))
    state.setdefault("last_bot_word", None)
    state.setdefault("last_bot_display", None)
    return state


def reset_state() -> None:
    state_id = session.get("state_id")
    if state_id and state_id in SESSION_STATE:
        SESSION_STATE[state_id] = initial_state()


def extract_last_word(message: str) -> Optional[tuple[str, int]]:
    matches = list(WORD_FINDER.finditer(message))
    if not matches:
        return None
    last = matches[-1].group()
    return last, len(matches)


def parse_followup_terms(message: str) -> Optional[List[str]]:
    for pattern in FOLLOWUP_PATTERNS:
        match = pattern.match(message)
        if not match:
            continue
        body = match.group("body")
        if not body:
            continue
        pieces = [
            part.strip("'\"- ")
            for part in re.split(r"[,\s]+", body)
            if part.strip("'\"- ")
        ]
        if len(pieces) >= 2:
            return pieces[:2]
    return None


def pick_reply_word(state: Dict[str, object], disallow: Optional[str] = None) -> Optional[str]:
    used = state["used"]
    bot_used = state["bot_used"]
    block = set(used) | set(bot_used)
    if disallow:
        block.add(normalize_term(disallow))
    candidates = [entry for entry in LEXICON if entry.normalized not in block]
    if not candidates:
        return None
    choice = random.choice(candidates)
    bot_used.add(choice.normalized)
    return choice.term


def make_nice_try_response(
    state: Dict[str, object], disallow: Optional[str] = None, callout: Optional[str] = None
) -> Dict[str, object]:
    reply_word = pick_reply_word(state, disallow=disallow)
    if reply_word:
        response = f"Nice try, {reply_word}."
    else:
        response = "Nice try."
    if callout:
        response = f"{response} I'm not your {callout.strip()}."
    return {"reply": append_score_suffix(response, 0), "score": 0}


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat() -> object:
    payload = request.get_json(force=True)
    message = (payload or {}).get("message", "")
    if not isinstance(message, str):
        return jsonify({"reply": "Say what now?", "score": get_state().get("score", 0)}), 400
    stripped = message.strip()
    if not stripped:
        return jsonify({"reply": "You gotta give me something, buddy.", "score": get_state().get("score", 0)})

    lowered = stripped.lower()
    if lowered in HIDDEN_COMMANDS:
        reply = "\n".join(f"{entry.rank}. {entry.term}" for entry in LEXICON)
        return jsonify({"reply": reply, "score": get_state().get("score", 0), "command": True})

    if lowered == "::reset":
        reset_state()
        return jsonify(
            {
                "reply": append_score_suffix("Fresh start. Hit me again.", 0),
                "score": 0,
                "command": True,
            }
        )

    state = get_state()
    last_bot_word = state.get("last_bot_word")

    if not last_bot_word:
        extraction = extract_last_word(stripped)
        if not extraction:
            reset_state()
            return jsonify({"reply": append_score_suffix("Ok.", 0), "score": 0})
        last_word, word_count = extraction
        normalized = normalize_term(last_word)
        if not normalized or normalized not in LEXICON_LOOKUP:
            fallback = "Hi" if word_count == 1 else "Ok."
            reset_state()
            return jsonify({"reply": append_score_suffix(fallback, 0), "score": 0})
        state["used"].add(normalized)
        state["score"] = 1
        reply_word = pick_reply_word(state, disallow=last_word)
        if not reply_word:
            reply_word = "buddy"
        state["last_bot_word"] = normalize_term(reply_word)
        state["last_bot_display"] = reply_word
        response = f"I'm not your {last_word.strip()}, {reply_word}."
        return jsonify({"reply": response, "score": state["score"]})

    terms = parse_followup_terms(stripped)
    if not terms:
        reset_state()
        return jsonify({"reply": append_score_suffix("Ok.", 0), "score": 0})

    word1_raw, word2_raw = terms
    normalized_word1 = normalize_term(word1_raw)
    normalized_word2 = normalize_term(word2_raw)

    if not normalized_word1 or not normalized_word2:
        reset_state()
        return jsonify({"reply": append_score_suffix("Ok.", 0), "score": 0})

    expected = state.get("last_bot_word")
    if not expected or normalized_word1 != expected:
        callout_display = state.get("last_bot_display") or state.get("last_bot_word") or "buddy"
        base = f"Nice try, {callout_display.strip()}."
        score = state.get("score", 0)
        reset_state()
        return jsonify({"reply": append_score_suffix(base, score), "score": 0})

    if normalized_word2 not in LEXICON_LOOKUP:
        response = make_nice_try_response(state, disallow=word2_raw, callout=word2_raw)
        reset_state()
        return jsonify(response)

    if normalized_word2 in state["used"] or normalized_word2 in state["bot_used"]:
        response = make_nice_try_response(state, disallow=word2_raw, callout=word2_raw)
        reset_state()
        return jsonify(response)

    state["used"].add(normalized_word2)
    state["score"] = state.get("score", 0) + 1
    reply_word = pick_reply_word(state, disallow=word2_raw)
    if not reply_word:
        reply_word = "buddy"
    state["last_bot_word"] = normalize_term(reply_word)
    state["last_bot_display"] = reply_word
    response = f"I'm not your {word2_raw.strip()}, {reply_word}."
    return jsonify({"reply": response, "score": state["score"]})


@app.route("/_list")
def show_list() -> object:
    return jsonify({"words": [{"rank": entry.rank, "term": entry.term} for entry in LEXICON]})


if __name__ == "__main__":
    app.run(debug=True)
