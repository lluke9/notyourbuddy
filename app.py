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


def normalize_term(term: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", term.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


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
    state = SESSION_STATE.setdefault(state_id, {"used": set(), "bot_used": set(), "score": 0})
    # ensure sets exist (for reloader)
    if not isinstance(state.get("used"), set):
        state["used"] = set(state.get("used", []))
    if not isinstance(state.get("bot_used"), set):
        state["bot_used"] = set(state.get("bot_used", []))
    return state


def reset_state() -> None:
    state_id = session.get("state_id")
    if state_id and state_id in SESSION_STATE:
        SESSION_STATE[state_id] = {"used": set(), "bot_used": set(), "score": 0}


def extract_terms(message: str) -> Optional[List[str]]:
    for pattern in INPUT_PATTERNS:
        match = pattern.match(message)
        if not match:
            continue
        raw_term = match.group("term")
        if not raw_term:
            continue
        pieces = [
            part.strip("'\"- ")
            for part in re.split(r"[,\s]+", raw_term)
            if part.strip("'\"- ")
        ]
        if pieces:
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


def make_nice_try_response(state: Dict[str, object], disallow: Optional[str] = None) -> Dict[str, object]:
    reply_word = pick_reply_word(state, disallow=disallow)
    if reply_word:
        response = f"Nice try, {reply_word}."
    else:
        response = "Nice try."
    score = state.get("score", 0)
    return {"reply": response, "score": score}


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
        return jsonify({"reply": "Fresh start. Hit me again.", "score": 0, "command": True})

    state = get_state()
    terms = extract_terms(stripped)
    if not terms:
        return jsonify({"reply": "Use a friendly nickname so I can clap back.", "score": state.get("score", 0)})
    processed_terms = []
    seen_in_message = set()
    for raw_term in terms:
        normalized = normalize_term(raw_term)
        if not normalized:
            continue
        if normalized in seen_in_message:
            return jsonify(make_nice_try_response(state, disallow=raw_term))
        seen_in_message.add(normalized)
        if normalized not in LEXICON_LOOKUP:
            return jsonify(make_nice_try_response(state, disallow=raw_term))
        if normalized in state["used"] or normalized in state["bot_used"]:
            return jsonify(make_nice_try_response(state, disallow=raw_term))
        processed_terms.append((raw_term, normalized))

    if not processed_terms:
        return jsonify(make_nice_try_response(state))

    for _, normalized in processed_terms:
        state["used"].add(normalized)

    state["score"] = state.get("score", 0) + 1
    reply_target = processed_terms[1][0] if len(processed_terms) > 1 else processed_terms[0][0]
    reply_word = pick_reply_word(state, disallow=reply_target)
    if not reply_word:
        reply_word = "...nobody"
    response = f"I'm not your {reply_target.strip()}, {reply_word}."
    return jsonify({"reply": response, "score": state["score"]})


@app.route("/_list")
def show_list() -> object:
    return jsonify({"words": [{"rank": entry.rank, "term": entry.term} for entry in LEXICON]})


if __name__ == "__main__":
    app.run(debug=True)
