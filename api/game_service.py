from __future__ import annotations

from chess.game import ChessGame
from chess.move import Move
from chess.rules import is_in_check, opponent_color


def format_move_san(game: ChessGame, move: Move) -> str:
    piece = game.board.get(move.from_square)
    is_capture = bool(move.captured_piece) or move.is_en_passant

    test_game = ChessGame.from_state(game.to_state())
    test_game.make_move(move)
    is_checkmate = test_game.state.status == "checkmate"
    is_check = is_in_check(test_game.board, test_game.state.turn) and not is_checkmate

    return move.to_san(piece, is_capture, is_check, is_checkmate)


def build_game_response(game_data: dict, chess_game: ChessGame) -> dict:
    legal_moves = [m.to_uci() for m in chess_game.legal_moves()]
    return {
        **game_data,
        "board_ascii": chess_game.board.to_ascii(),
        "legal_moves": legal_moves,
        "in_check": chess_game.get_check_status(),
        "is_game_over": chess_game.is_game_over(),
    }


def validate_player_turn(game_data: dict, player_name: str) -> None:
    if game_data["mode"] != "pvp":
        return

    turn = game_data["state"]["turn"]
    white = game_data["white_player"]
    black = game_data["black_player"]

    if turn == "white" and player_name != white:
        raise ValueError("Not white player's turn")
    if turn == "black" and player_name != black:
        raise ValueError("Not black player's turn")


def validate_not_ai_turn(game_data: dict) -> None:
    if game_data["mode"] != "vs_ai":
        return

    ai_color = game_data["ai_color"]
    if game_data["state"]["turn"] == ai_color:
        raise ValueError("It is the AI's turn. Call /ai-move instead.")


def get_human_color(game_data: dict) -> str:
    if game_data["mode"] == "vs_ai":
        return opponent_color(game_data["ai_color"])
    return game_data["state"]["turn"]
