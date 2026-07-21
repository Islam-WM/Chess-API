"""Einfacher Test-Runner ohne pytest-Abhängigkeit."""

from __future__ import annotations

import tempfile
import traceback
from pathlib import Path

from chess.game import ChessGame
from chess.move import Move
from storage.database import GameRepository


def run_test(name: str, fn) -> None:
    try:
        fn()
        print(f"PASS: {name}")
    except Exception as exc:
        print(f"FAIL: {name}")
        traceback.print_exc()
        raise exc


def test_initial_position_20_legal_moves():
    game = ChessGame()
    assert len(game.legal_moves()) == 20


def test_pawn_move_and_en_passant_setup():
    game = ChessGame()
    game.make_move_uci("e2e4")
    game.make_move_uci("a7a6")
    game.make_move_uci("e4e5")
    game.make_move_uci("d7d5")
    assert game.state.en_passant_target == "d6"


def test_en_passant_capture():
    game = ChessGame()
    for uci in ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"]:
        game.make_move_uci(uci)
    assert game.board.get("d6") == "P"
    assert game.board.get("d5") is None


def test_castling_kingside_white():
    game = ChessGame()
    for uci in ["e2e4", "a7a6", "g1f3", "a6a5", "f1c4", "a5a4", "e1g1"]:
        game.make_move_uci(uci)
    assert game.board.get("g1") == "K"
    assert game.board.get("f1") == "R"


def test_pawn_promotion():
    game = ChessGame()
    board = game.board
    for sq in board.all_squares():
        board.set(sq, None)
    board.set("a7", "P")
    board.set("h8", "k")
    board.set("h1", "K")
    game.state.board = board.to_dict()
    game.state.turn = "white"
    game.state.castling_rights = {
        "white_kingside": False,
        "white_queenside": False,
        "black_kingside": False,
        "black_queenside": False,
    }
    game.make_move(Move("a7", "a8", promotion="Q"))
    assert game.board.get("a8") == "Q"


def test_repository_saves_moves():
    with tempfile.TemporaryDirectory() as tmp:
        repo = GameRepository(db_path=Path(tmp) / "test.db")
        game = repo.create_game(mode="pvp", white_player="Alice")
        repo.join_game(game["id"], "Bob")
        chess = repo.load_chess_game(game["id"])
        move = chess.make_move_uci("e2e4")
        repo.save_move(game["id"], move, "e4", chess.to_state())
        history = repo.get_moves(game["id"])
        assert len(history) == 1
        assert history[0]["uci"] == "e2e4"


if __name__ == "__main__":
    tests = [
        ("initial moves", test_initial_position_20_legal_moves),
        ("en passant setup", test_pawn_move_and_en_passant_setup),
        ("en passant capture", test_en_passant_capture),
        ("castling", test_castling_kingside_white),
        ("promotion", test_pawn_promotion),
        ("repository", test_repository_saves_moves),
    ]
    for name, fn in tests:
        run_test(name, fn)
    print("Alle Kern-Tests bestanden.")
