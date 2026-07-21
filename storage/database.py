from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from chess.game import ChessGame
from chess.move import GameState, Move

DB_PATH = Path(__file__).parent.parent / "data" / "chess.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GameRepository:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    white_player TEXT,
                    black_player TEXT,
                    ai_color TEXT,
                    ai_engine TEXT,
                    status TEXT NOT NULL,
                    winner TEXT,
                    result_reason TEXT,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    move_number INTEGER NOT NULL,
                    color TEXT NOT NULL,
                    uci TEXT NOT NULL,
                    san TEXT,
                    fen_after TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );
                """
            )

    def create_game(
        self,
        mode: str,
        white_player: str | None = None,
        black_player: str | None = None,
        ai_color: str | None = None,
        ai_engine: str | None = None,
    ) -> dict:
        game_id = str(uuid.uuid4())
        game = ChessGame()
        state = game.to_state()
        now = _utc_now()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO games (
                    id, mode, white_player, black_player, ai_color, ai_engine,
                    status, winner, result_reason, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    mode,
                    white_player,
                    black_player,
                    ai_color,
                    ai_engine,
                    state.status,
                    state.winner,
                    state.result_reason,
                    json.dumps(self._state_to_dict(state)),
                    now,
                    now,
                ),
            )

        return self.get_game(game_id)

    def get_game(self, game_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
            if not row:
                return None
            return self._row_to_game(row)

    def list_games(self, status: str | None = None) -> list[dict]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM games WHERE status = ? ORDER BY updated_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM games ORDER BY updated_at DESC").fetchall()
            return [self._row_to_game(row) for row in rows]

    def join_game(self, game_id: str, player_name: str) -> dict:
        game = self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")
        if game["mode"] != "pvp":
            raise ValueError("Only PvP games can be joined")

        white = game["white_player"]
        black = game["black_player"]

        if white and black:
            raise ValueError("Game is already full")
        if player_name in {white, black}:
            return game

        field = "black_player" if white else "white_player"
        with self._connect() as conn:
            conn.execute(
                f"UPDATE games SET {field} = ?, updated_at = ? WHERE id = ?",
                (player_name, _utc_now(), game_id),
            )
        return self.get_game(game_id)

    def save_move(
        self,
        game_id: str,
        move: Move,
        san: str,
        state: GameState,
    ) -> None:
        move_number = state.fullmove_number if state.turn == WHITE else state.fullmove_number
        color = BLACK if state.turn == WHITE else WHITE

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO moves (game_id, move_number, color, uci, san, fen_after, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (game_id, move_number, color, move.to_uci(), san, state.to_fen(), _utc_now()),
            )
            conn.execute(
                """
                UPDATE games
                SET state_json = ?, status = ?, winner = ?, result_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(self._state_to_dict(state)),
                    state.status,
                    state.winner,
                    state.result_reason,
                    _utc_now(),
                    game_id,
                ),
            )

    def get_moves(self, game_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM moves WHERE game_id = ? ORDER BY id ASC",
                (game_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def load_chess_game(self, game_id: str) -> ChessGame:
        game = self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")
        state = self._dict_to_state(game["state"])
        return ChessGame.from_state(state)

    def update_state(self, game_id: str, state: GameState) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE games
                SET state_json = ?, status = ?, winner = ?, result_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(self._state_to_dict(state)),
                    state.status,
                    state.winner,
                    state.result_reason,
                    _utc_now(),
                    game_id,
                ),
            )

    @staticmethod
    def _state_to_dict(state: GameState) -> dict:
        return {
            "board": state.board,
            "turn": state.turn,
            "castling_rights": state.castling_rights,
            "en_passant_target": state.en_passant_target,
            "halfmove_clock": state.halfmove_clock,
            "fullmove_number": state.fullmove_number,
            "status": state.status,
            "winner": state.winner,
            "result_reason": state.result_reason,
        }

    @staticmethod
    def _dict_to_state(data: dict) -> GameState:
        return GameState(
            board=data["board"],
            turn=data["turn"],
            castling_rights=data["castling_rights"],
            en_passant_target=data.get("en_passant_target"),
            halfmove_clock=data.get("halfmove_clock", 0),
            fullmove_number=data.get("fullmove_number", 1),
            status=data.get("status", "active"),
            winner=data.get("winner"),
            result_reason=data.get("result_reason"),
        )

    def _row_to_game(self, row: sqlite3.Row) -> dict:
        state_data = json.loads(row["state_json"])
        game_state = self._dict_to_state(state_data)
        return {
            "id": row["id"],
            "mode": row["mode"],
            "white_player": row["white_player"],
            "black_player": row["black_player"],
            "ai_color": row["ai_color"],
            "ai_engine": row["ai_engine"],
            "status": row["status"],
            "winner": row["winner"],
            "result_reason": row["result_reason"],
            "state": state_data,
            "fen": game_state.to_fen(),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


WHITE = "white"
BLACK = "black"
