# Shivam & GF's Multiplayer Game Zone

A small real-time web app (Flask + Socket.IO) where two people can play
mini-games together from a shared link, even from different cities.

Games: Tic Tac Toe, Rock Paper Scissors, Reflex Race.

## 1. Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** — click "Create a Room", enter your name,
you'll land in a room with a code (e.g. `XJ4K9`) and a shareable link.

## 2. Let your girlfriend join from far away

Running on `localhost` only works on your own computer — she can't reach
that over the internet. You have two options:

### Option A — Quick & free (temporary link, good for playing right now)
1. Keep `python app.py` running.
2. Download **ngrok**: https://ngrok.com/download (free account).
3. In a *new* terminal window run:
   ```bash
   ngrok http 5000
   ```
4. ngrok prints a public URL like `https://abcd-1234.ngrok-free.app`.
5. Open that URL yourself, create the room — the link shown in your
   browser will now be the ngrok URL. Send that link to your girlfriend.
6. She opens it, types her name, and joins your room. Pick a game and play!

   Note: the free ngrok URL changes every time you restart ngrok, and the
   free tunnel closes if left idle too long — fine for a quick play session.

### Option B — Permanent link (deploy it properly)
Deploy this app to a free host such as **Render.com** or **Railway.app**:
1. Push this folder to a GitHub repo.
2. On Render.com: New → Web Service → connect the repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `python app.py`
3. Render gives you a permanent URL like `https://your-app.onrender.com`
   that both of you can use anytime, no ngrok needed.

## 3. How to play
- One of you clicks **Create a Room** → gets a room code + link.
- Share the link (or just the code, via the Join box) with the other.
- Once both of you have joined, either person picks a game from the menu.
- Play! Use **Back to Menu** anytime to switch games.

## Notes
- This keeps game state in memory — restarting the server clears all rooms.
- Two players max per room (built for the two of you).
