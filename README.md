# SiteSuprise

## The Whole Point
This project exists for one reason: every 10 minutes, an AI generates a totally new web design for the main page. No two layouts are ever the same. Sometimes it’s gorgeous, sometimes it’s a hot mess, but it’s always fresh. I built this because I was bored of static sites and wanted something that felt alive (or at least unpredictable).


## Setup
Clone the repo, run the backend, and open the HTML file:

```bash
cd api
python3 main.py
```

Then open `index.html` in your browser. No build tools, no dependencies (except Python 3.11+). If it breaks, well, you get to keep both pieces.

## How It Works
- The backend (see `api/main.py`) runs a little AI routine that spits out a new design every 10 minutes.
- The frontend (`index.html`) reloads and shows off whatever the AI came up with. Sometimes you’ll get a modern look, sometimes it’ll look like a forgotten Geocities page. That’s half the fun.
- No manual refresh needed—just leave the page open and watch it morph. Or hit reload if you’re impatient.

## Why?
Mostly for fun. Also for testing weird frontend ideas and seeing what happens when you let an AI run wild with design choices. If you want to contribute, open a PR or issue, or just fork it and make it weirder.

---
If you have questions, just ping me. Or don’t. It’s your life.