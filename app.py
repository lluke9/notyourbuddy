import json
import os
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


def normalize_term(term: str) -> str:
    lowered = term.lower()
    lowered = re.sub(r"[^a-z0-9\-]+", " ", lowered)
    lowered = re.sub(r"\s*\-\s*", "-", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


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
LEXICON_BY_NORMALIZED: Dict[str, WordEntry] = {entry.normalized: entry for entry in LEXICON}


def build_patterns() -> List[Pattern[str]]:
    raw_patterns = [
        r"^\s*hey\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hey there\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*heya\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hiya\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hi\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hello\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*yo\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*yoo\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*yooo+\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*y'all\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*supp?\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*wass?up\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*what'?s up\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*greetings\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*salutations\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*good (?:morning|evening|afternoon|day)\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*ahoy\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*oi\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*oy\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hey yo\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*listen\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*look here\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*alright\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*okay\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*dear\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*dearest\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*my\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hey my\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*listen up\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hear me\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*hear this\s+(?P<term>[\w'\- ]+?)\s*[!.?]*$",
        r"^\s*i[' ]?m not your\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*i am not your\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*i[' ]?m not yo\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*i[' ]?m not ya\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*i[' ]?m not ur\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*im not your\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*im not yo\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*im not ya\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*im not ur\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*not your\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*not yo\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*not ya\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*not ur\s+(?P<term>[\w'\- ,]+?)\s*$",
        r"^\s*no more\s+(?P<term>[\w'\- ]+?)\s*$",
        r"^\s*forget it\s+(?P<term>[\w'\- ]+?)\s*$",
        r"^\s*cut it out\s+(?P<term>[\w'\- ]+?)\s*$",
        r"^\s*quit it\s+(?P<term>[\w'\- ]+?)\s*$",
        r"^\s*drop it\s+(?P<term>[\w'\- ]+?)\s*$",
        r"^\s*stop it\s+(?P<term>[\w'\- ]+?)\s*$",
    ]
    patterns = [re.compile(pat, re.IGNORECASE) for pat in raw_patterns]
    return patterns


INPUT_PATTERNS = build_patterns()

SESSION_STATE: Dict[str, Dict[str, object]] = {}

HIDDEN_COMMANDS = {"::list", "/list", "/words", "/ranked", "list please", "show list"}


def get_state() -> Dict[str, object]:
    state_id = session.get("state_id")
    if not state_id:
        state_id = uuid.uuid4().hex
        session["state_id"] = state_id
    state = SESSION_STATE.setdefault(
        state_id,
        {"used": set(), "bot_used": set(), "score": 0, "last_bot_word": LEXICON[0].term if LEXICON else "buddy"},
    )
    # ensure sets exist (for reloader)
    if not isinstance(state.get("used"), set):
        state["used"] = set(state.get("used", []))
    if not isinstance(state.get("bot_used"), set):
        state["bot_used"] = set(state.get("bot_used", []))
    if not state.get("last_bot_word"):
        state["last_bot_word"] = LEXICON[0].term if LEXICON else "buddy"
    return state


def reset_state() -> None:
    state_id = session.get("state_id")
    if state_id and state_id in SESSION_STATE:
        SESSION_STATE[state_id] = {
            "used": set(),
            "bot_used": set(),
            "score": 0,
            "last_bot_word": LEXICON[0].term if LEXICON else "buddy",
        }


def last_bot_word(state: Dict[str, object]) -> str:
    word = state.get("last_bot_word") if isinstance(state, dict) else None
    if not word:
        return LEXICON[0].term if LEXICON else "buddy"
    return word


def extract_terms(message: str) -> List[str]:
    for pattern in INPUT_PATTERNS:
        match = pattern.match(message)
        if match:
            raw_term = match.group("term")
            if not raw_term:
                continue
            pieces = re.split(r"[\s,/\\]+", raw_term)
            terms = []
            for piece in pieces:
                cleaned = piece.strip("'\"")
                if cleaned:
                    terms.append(cleaned)
            if terms:
                return terms
    return []


def pick_reply_word(state: Dict[str, object], disallow: Optional[str] = None) -> Optional[str]:
    used = state["used"]
    bot_used = state["bot_used"]
    block = set(used) | set(bot_used)
    if disallow:
        block.add(disallow)
    for entry in LEXICON:
        if entry.normalized not in block:
            bot_used.add(entry.normalized)
            state["last_bot_word"] = entry.term
            return entry.term
    return None


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat() -> object:
    payload = request.get_json(force=True)
    message = (payload or {}).get("message", "")
    if not isinstance(message, str):
        state = get_state()
        return (
            jsonify({"reply": f"What's that, {last_bot_word(state)}?", "score": state.get("score", 0)}),
            400,
        )
    stripped = message.strip()
    if not stripped:
        state = get_state()
        return jsonify({"reply": f"What's that, {last_bot_word(state)}?", "score": state.get("score", 0)})

    lowered = stripped.lower()
    if lowered in HIDDEN_COMMANDS:
        reply = "\n".join(f"{entry.rank}. {entry.term}" for entry in LEXICON)
        return jsonify({"reply": reply, "score": get_state().get("score", 0), "command": True})

    if lowered == "::reset":
        reset_state()
        return jsonify({"reply": "Fresh start. Hit me again.", "score": 0, "command": True})

    state = get_state()
    terms = extract_terms(stripped)
    if not terms:
        return jsonify({"reply": f"What's that, {last_bot_word(state)}?", "score": state.get("score", 0)})

    normalized_terms: List[str] = []
    canonical_terms: List[str] = []
    for term in terms:
        normalized = normalize_term(term)
        if not normalized:
            continue
        entry = LEXICON_BY_NORMALIZED.get(normalized)
        if not entry:
            return jsonify({
                "reply": f"What's that, {last_bot_word(state)}?",
                "score": state.get("score", 0),
            })
        normalized_terms.append(entry.normalized)
        canonical_terms.append(entry.term)

    if not normalized_terms:
        return jsonify({"reply": f"What's that, {last_bot_word(state)}?", "score": state.get("score", 0)})

    user_norm = normalized_terms[0]
    response_norm = normalized_terms[-1]

    if user_norm in state["used"] or user_norm in state["bot_used"]:
        reply_word = pick_reply_word(state, disallow=user_norm)
        score = state.get("score", 0)
        if reply_word:
            response = f"You ruined it, {reply_word}! Score: {score}."
        else:
            response = f"You ruined it, but I'm out of comebacks. Score: {score}."
        return jsonify({"reply": response, "score": score})

    if response_norm in state["used"] or response_norm in state["bot_used"]:
        reply_word = pick_reply_word(state, disallow=response_norm)
        score = state.get("score", 0)
        if reply_word:
            response = f"You ruined it, {reply_word}! Score: {score}."
        else:
            response = f"You ruined it, but I'm out of comebacks. Score: {score}."
        return jsonify({"reply": response, "score": score})

    state["used"].add(user_norm)
    for extra_norm in normalized_terms[1:]:
        state["used"].add(extra_norm)
    state["score"] = state.get("score", 0) + 1
    reply_word = pick_reply_word(state, disallow=response_norm)
    if not reply_word:
        reply_word = "...nobody"
        state["last_bot_word"] = reply_word
    response = f"I'm not your {canonical_terms[-1]}, {reply_word}."
    return jsonify({"reply": response, "score": state["score"]})


@app.route("/_list")
def show_list() -> object:
    return jsonify({"words": [{"rank": entry.rank, "term": entry.term} for entry in LEXICON]})


if __name__ == "__main__":
    app.run(debug=True)
