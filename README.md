# Not Your Buddy

A stylized Flask web toy that riffs on the classic South Park banter loop. Challenge the bot with as many unique nicknames as you can without repeating yourself — it tracks your score, dishes out fresh comebacks from a 1,200-term ranked lexicon, and calls you out the moment you slip.

## Features

- 🎯 **Ranked lexicon** of 1,200 nickname-style terms sorted by meme-worthiness and familiarity.
- 🧠 **Variation-aware parser** that understands 50+ greeting formats like “hey bro”, “im not yo buddy, pal”, or “not ur champ champ”.
- 🔁 **Session scoring** that praises unique flair and warns you with “You ruined it” the moment you repeat a word.
- 🪄 **Hidden commands** such as `::list` for the full ranked roster and `::reset` to start over.
- 💅 **Stylized UI** with glassmorphism, gradient flare, and built-in domain inspiration.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Visit <http://localhost:5000> and start the banter.

## Hidden routes & commands

- `/_list` – JSON dump of the ranked lexicon (great for QA or export).
- In chat, send `::list` to see the ranked words or `::reset` to clear your session.

## Future ideas

- Persist high scores with a lightweight database.
- Add multiplayer lobbies or daily streaks.
- Spin up at **notyourbuddy.com**, **notyobro.com**, or **brobot.chat** for maximum meme energy.
