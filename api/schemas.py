from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreatePvPGameRequest(BaseModel):
    white_player: str = Field(..., min_length=1, max_length=50)


class JoinGameRequest(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=50)


class CreateAIGameRequest(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=50)
    player_color: Literal["white", "black"] = "white"
    ai_engine: Literal["heuristic", "stockfish", "random"] = "heuristic"
    ai_depth: int = Field(default=3, ge=1, le=5)


class MoveRequest(BaseModel):
    uci: str = Field(..., min_length=4, max_length=5, regex=r"^[a-h][1-8][a-h][1-8][qrbn]?$")
    player_name: str | None = None


class GameResponse(BaseModel):
    id: str
    mode: str
    white_player: str | None
    black_player: str | None
    ai_color: str | None
    ai_engine: str | None
    status: str
    winner: str | None
    result_reason: str | None
    fen: str
    board_ascii: str
    legal_moves: list[str]
    in_check: bool
    is_game_over: bool
    state: dict
    created_at: str
    updated_at: str


class MoveHistoryItem(BaseModel):
    id: int
    game_id: str
    move_number: int
    color: str
    uci: str
    san: str | None
    fen_after: str
    created_at: str


class MoveResultResponse(BaseModel):
    move: dict
    game: GameResponse
