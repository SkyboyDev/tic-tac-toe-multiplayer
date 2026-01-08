from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict

app = FastAPI()

# Serve static files properly
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")

rooms: Dict[str, Dict] = {}

def check_winner(board):
    wins = [
        [0,1,2],[3,4,5],[6,7,8],
        [0,3,6],[1,4,7],[2,5,8],
        [0,4,8],[2,4,6]
    ]
    for a,b,c in wins:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "draw"
    return None

@app.websocket("/ws/{room}/{name}")
async def game_ws(ws: WebSocket, room: str, name: str):
    await ws.accept()

    if room not in rooms:
        rooms[room] = {
            "players": [],
            "board": [""] * 9,
            "turn": "X"
        }

    room_data = rooms[room]

    if len(room_data["players"]) >= 2:
        await ws.send_json({"error": "Room full"})
        await ws.close()
        return

    symbol = "X" if len(room_data["players"]) == 0 else "O"
    room_data["players"].append({"ws": ws, "symbol": symbol})

    for p in room_data["players"]:
        await p["ws"].send_json({
            "type": "start",
            "symbol": p["symbol"],
            "board": room_data["board"],
            "turn": room_data["turn"]
        })

    try:
        while True:
            data = await ws.receive_json()
            idx = data["index"]

            if room_data["board"][idx] or room_data["turn"] != symbol:
                continue

            room_data["board"][idx] = symbol
            winner = check_winner(room_data["board"])
            room_data["turn"] = "O" if room_data["turn"] == "X" else "X"

            for p in room_data["players"]:
                await p["ws"].send_json({
                    "type": "update",
                    "board": room_data["board"],
                    "turn": room_data["turn"],
                    "winner": winner
                })

    except WebSocketDisconnect:
        room_data["players"] = [p for p in room_data["players"] if p["ws"] != ws]
        if not room_data["players"]:
            del rooms[room]

