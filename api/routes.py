from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai import get_ai
from api.game_service import (
    build_game_response,
    format_move_san,
    validate_not_ai_turn,
    validate_player_turn,
)
from api.schemas import (
    CreateAIGameRequest,
    CreatePvPGameRequest,
    GameResponse,
    JoinGameRequest,
    MoveHistoryItem,
    MoveRequest,
    MoveResultResponse,
)
from chess.game import ChessGame
from chess.move import Move
from storage.database import GameRepository

router = APIRouter()
repo = GameRepository()


def _get_game_or_404(game_id: str) -> dict:
    game = repo.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "schach-api"}


@router.post("/games/pvp", response_model=GameResponse)
def create_pvp_game(request: CreatePvPGameRequest) -> dict:
    game = repo.create_game(mode="pvp", white_player=request.white_player)
    chess_game = repo.load_chess_game(game["id"])
    return build_game_response(game, chess_game)


@router.post("/games/{game_id}/join", response_model=GameResponse)
def join_pvp_game(game_id: str, request: JoinGameRequest) -> dict:
    try:
        game = repo.join_game(game_id, request.player_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chess_game = repo.load_chess_game(game_id)
    return build_game_response(game, chess_game)


@router.post("/games/vs-ai", response_model=GameResponse)
def create_ai_game(request: CreateAIGameRequest) -> dict:
    ai_color = "black" if request.player_color == "white" else "white"
    white_player = request.player_name if request.player_color == "white" else "AI"
    black_player = request.player_name if request.player_color == "black" else "AI"

    game = repo.create_game(
        mode="vs_ai",
        white_player=white_player,
        black_player=black_player,
        ai_color=ai_color,
        ai_engine=request.ai_engine,
    )
    chess_game = repo.load_chess_game(game["id"])
    response = build_game_response(game, chess_game)

    if game["state"]["turn"] == ai_color:
        return _execute_ai_move(game["id"], request.ai_engine, request.ai_depth)

    return response


@router.get("/games", response_model=list[GameResponse])
def list_games(status: str | None = None) -> list[dict]:
    games = repo.list_games(status=status)
    result = []
    for game in games:
        chess_game = repo.load_chess_game(game["id"])
        result.append(build_game_response(game, chess_game))
    return result


@router.get("/games/{game_id}", response_model=GameResponse)
def get_game(game_id: str) -> dict:
    game = _get_game_or_404(game_id)
    chess_game = repo.load_chess_game(game_id)
    return build_game_response(game, chess_game)


@router.get("/games/{game_id}/moves", response_model=list[MoveHistoryItem])
def get_game_moves(game_id: str) -> list[dict]:
    _get_game_or_404(game_id)
    return repo.get_moves(game_id)


@router.get("/games/{game_id}/legal-moves")
def get_legal_moves(game_id: str) -> dict:
    game = _get_game_or_404(game_id)
    chess_game = repo.load_chess_game(game_id)
    return {
        "game_id": game_id,
        "turn": game["state"]["turn"],
        "legal_moves": [m.to_uci() for m in chess_game.legal_moves()],
    }


@router.post("/games/{game_id}/move", response_model=MoveResultResponse)
def make_move(game_id: str, request: MoveRequest) -> dict:
    game = _get_game_or_404(game_id)
    chess_game = repo.load_chess_game(game_id)

    if chess_game.is_game_over():
        raise HTTPException(status_code=400, detail="Game is already over")

    if request.player_name:
        try:
            validate_player_turn(game, request.player_name)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        validate_not_ai_turn(game)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pre_move_game = ChessGame.from_state(repo._dict_to_state(game["state"]))
    try:
        move = chess_game.make_move(Move.from_uci(request.uci))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    san = format_move_san(pre_move_game, move)
    repo.save_move(game_id, move, san, chess_game.to_state())

    updated_game = repo.get_game(game_id)
    updated_chess = repo.load_chess_game(game_id)

    return {
        "move": {
            "uci": move.to_uci(),
            "san": san,
            "captured": move.captured_piece,
            "is_castling": move.is_castling,
            "is_en_passant": move.is_en_passant,
            "promotion": move.promotion,
        },
        "game": build_game_response(updated_game, updated_chess),
    }


@router.post("/games/{game_id}/ai-move", response_model=MoveResultResponse)
def ai_move(game_id: str, depth: int = 3, engine: str | None = None) -> dict:
    game = _get_game_or_404(game_id)

    if game["mode"] != "vs_ai":
        raise HTTPException(status_code=400, detail="This game is not an AI game")

    return _execute_ai_move(
        game_id,
        engine or game["ai_engine"] or "heuristic",
        depth,
    )


def _execute_ai_move(game_id: str, engine: str, depth: int) -> dict:
    game = repo.get_game(game_id)
    chess_game = repo.load_chess_game(game_id)

    if chess_game.is_game_over():
        raise HTTPException(status_code=400, detail="Game is already over")

    ai_color = game["ai_color"]
    if chess_game.state.turn != ai_color:
        raise HTTPException(status_code=400, detail="It is not the AI's turn")

    ai = get_ai(engine, depth=depth)
    try:
        move = ai.choose_move(chess_game)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pre_move_game = ChessGame.from_state(chess_game.to_state())
    executed = chess_game.make_move(move)
    san = format_move_san(pre_move_game, executed)
    repo.save_move(game_id, executed, san, chess_game.to_state())

    updated_game = repo.get_game(game_id)
    updated_chess = repo.load_chess_game(game_id)

    return {
        "move": {
            "uci": executed.to_uci(),
            "san": san,
            "captured": executed.captured_piece,
            "is_castling": executed.is_castling,
            "is_en_passant": executed.is_en_passant,
            "promotion": executed.promotion,
            "engine": engine,
        },
        "game": build_game_response(updated_game, updated_chess),
    }
