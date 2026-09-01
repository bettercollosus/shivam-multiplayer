"""
Shivam & GF's Multiplayer Game Zone
------------------------------------
A small Flask + Socket.IO web app that lets two people play together in
real time from a shared link (room code), even if they're far apart.

Games included:
  - Tic Tac Toe   (turn based)
  - Rock Paper Scissors (simultaneous choice)
  - Reflex Race   (who clicks fastest after GO)

HOW TO RUN LOCALLY:
    pip install -r requirements.txt
    python app.py
  Then open http://localhost:5000 in your browser.

HOW TO SHARE A LINK WITH SOMEONE FAR AWAY (quick way):
  1. Run the app as above (keep it running).
  2. Install ngrok (https://ngrok.com/download), sign up (free).
  3. In a new terminal run:  ngrok http 5000
  4. ngrok gives you a public URL like https://abcd1234.ngrok-free.app
  5. Share THAT link with your girlfriend instead of localhost.
     She opens it, joins your room code, and you're both in the same game.

  (ngrok's free URL changes each time you restart it. For a permanent
   link, deploy this app to a free host like Render.com or Railway.app —
   see README.md for steps.)
"""

import random
import string
import time
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "shivam-secret-key-change-me"
socketio = SocketIO(app, async_mode="threading")

# ---------------------------------------------------------------------------
# In-memory room storage (fine for a small app between 2 people).
# rooms[room_id] = {
#     "players": [{"sid": str, "name": str}, ...]   # max 2
#     "game": None | "ttt" | "rps" | "reflex"
#     "state": { ...game specific state... }
# }
# ---------------------------------------------------------------------------
rooms = {}
sid_to_room = {}   # socket id -> room_id


def generate_room_code():
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in rooms:
            return code


def new_ttt_state():
    return {"board": [""] * 9, "turn": "X", "winner": None}


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create", methods=["POST"])
def create_room():
    name = request.form.get("name", "Player").strip() or "Player"
    room_id = generate_room_code()
    rooms[room_id] = {"players": [], "game": None, "state": {}}
    return redirect(url_for("room", room_id=room_id, name=name))


@app.route("/join", methods=["POST"])
def join_room_route():
    name = request.form.get("name", "Player").strip() or "Player"
    room_id = request.form.get("room_id", "").strip().upper()
    if room_id not in rooms:
        return render_template("index.html", error="Room not found. Check the code!")
    return redirect(url_for("room", room_id=room_id, name=name))


@app.route("/room/<room_id>")
def room(room_id):
    name = request.args.get("name", "Player")
    if room_id not in rooms:
        rooms[room_id] = {"players": [], "game": None, "state": {}}
    return render_template("room.html", room_id=room_id, name=name)


# ---------------------------------------------------------------------------
# SOCKET.IO EVENTS
# ---------------------------------------------------------------------------
@socketio.on("join")
def on_join(data):
    room_id = data["room_id"]
    name = data["name"]

    if room_id not in rooms:
        rooms[room_id] = {"players": [], "game": None, "state": {}}

    room_data = rooms[room_id]

    if len(room_data["players"]) >= 2:
        emit("room_full")
        return

    join_room(room_id)
    sid_to_room[request.sid] = room_id
    room_data["players"].append({"sid": request.sid, "name": name})

    player_index = len(room_data["players"]) - 1
    emit("joined", {"player_index": player_index, "room_id": room_id})

    names = [p["name"] for p in room_data["players"]]
    emit("player_list", {"players": names}, room=room_id)

    if len(room_data["players"]) == 2:
        emit("ready_to_play", room=room_id)


@socketio.on("disconnect")
def on_disconnect():
    room_id = sid_to_room.pop(request.sid, None)
    if not room_id or room_id not in rooms:
        return
    room_data = rooms[room_id]
    room_data["players"] = [p for p in room_data["players"] if p["sid"] != request.sid]
    names = [p["name"] for p in room_data["players"]]
    emit("player_list", {"players": names}, room=room_id)
    emit("opponent_left", room=room_id)
    if not room_data["players"]:
        rooms.pop(room_id, None)


@socketio.on("select_game")
def on_select_game(data):
    room_id = data["room_id"]
    game = data["game"]
    room_data = rooms.get(room_id)
    if not room_data:
        return

    room_data["game"] = game
    if game == "ttt":
        room_data["state"] = new_ttt_state()
    elif game == "rps":
        room_data["state"] = {"choices": {}}
    elif game == "reflex":
        room_data["state"] = {"go_time": None, "results": {}}

    emit("game_selected", {"game": game}, room=room_id)


# ---------------- TIC TAC TOE ----------------
@socketio.on("ttt_move")
def on_ttt_move(data):
    room_id = data["room_id"]
    index = data["index"]
    room_data = rooms.get(room_id)
    if not room_data or room_data["game"] != "ttt":
        return

    state = room_data["state"]
    players = room_data["players"]
    player_index = next(
        (i for i, p in enumerate(players) if p["sid"] == request.sid), None
    )
    if player_index is None:
        return

    symbol = "X" if player_index == 0 else "O"
    if state["winner"] or state["turn"] != symbol or state["board"][index] != "":
        return

    state["board"][index] = symbol
    winner = check_ttt_winner(state["board"])
    if winner:
        state["winner"] = winner
    else:
        state["turn"] = "O" if symbol == "X" else "X"

    emit("ttt_update", state, room=room_id)


@socketio.on("ttt_restart")
def on_ttt_restart(data):
    room_id = data["room_id"]
    room_data = rooms.get(room_id)
    if not room_data:
        return
    room_data["state"] = new_ttt_state()
    emit("ttt_update", room_data["state"], room=room_id)


def check_ttt_winner(board):
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(cell != "" for cell in board):
        return "Draw"
    return None


# ---------------- ROCK PAPER SCISSORS ----------------
@socketio.on("rps_choice")
def on_rps_choice(data):
    room_id = data["room_id"]
    choice = data["choice"]
    room_data = rooms.get(room_id)
    if not room_data or room_data["game"] != "rps":
        return

    state = room_data["state"]
    state["choices"][request.sid] = choice
    emit("rps_waiting", {"who": request.sid}, room=room_id)

    if len(state["choices"]) == 2:
        players = room_data["players"]
        p1, p2 = players[0], players[1]
        c1, c2 = state["choices"][p1["sid"]], state["choices"][p2["sid"]]
        result = decide_rps(c1, c2)

        emit(
            "rps_result",
            {
                "p1_name": p1["name"], "p1_choice": c1,
                "p2_name": p2["name"], "p2_choice": c2,
                "result": result,
            },
            room=room_id,
        )
        state["choices"] = {}


def decide_rps(c1, c2):
    if c1 == c2:
        return "draw"
    beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    return "p1" if beats[c1] == c2 else "p2"


# ---------------- REFLEX RACE ----------------
@socketio.on("reflex_start")
def on_reflex_start(data):
    room_id = data["room_id"]
    room_data = rooms.get(room_id)
    if not room_data or room_data["game"] != "reflex":
        return

    room_data["state"] = {"go_time": None, "results": {}}
    delay = random.uniform(2.0, 5.0)
    socketio.sleep(delay)

    room_data["state"]["go_time"] = time.time()
    emit("reflex_go", room=room_id)


@socketio.on("reflex_click")
def on_reflex_click(data):
    room_id = data["room_id"]
    room_data = rooms.get(room_id)
    if not room_data or room_data["game"] != "reflex":
        return

    state = room_data["state"]
    if state["go_time"] is None or request.sid in state["results"]:
        return

    elapsed_ms = round((time.time() - state["go_time"]) * 1000)
    state["results"][request.sid] = elapsed_ms

    players = room_data["players"]
    if len(state["results"]) == len(players) and len(players) == 2:
        p1, p2 = players[0], players[1]
        t1 = state["results"].get(p1["sid"])
        t2 = state["results"].get(p2["sid"])
        emit(
            "reflex_result",
            {"p1_name": p1["name"], "p1_time": t1, "p2_name": p2["name"], "p2_time": t2},
            room=room_id,
        )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
