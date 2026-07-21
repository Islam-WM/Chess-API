from __future__ import annotations

import tempfile
from pathlib import Path

from chess.game import ChessGame
from chess.move import Move
from storage.database import GameRepository


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
    moves = ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"]
    for uci in moves:
        game.make_move_uci(uci)
    assert game.board.get("d6") == "P"
    assert game.board.get("d5") is None


def test_castling_kingside_white():
    game = ChessGame()
    for uci in ["e2e4", "a7a6", "g1f3", "a6a5", "f1c4", "a5a4", "e1g1"]:
        game.make_move_uci(uci)
    assert game.board.get("g1") == "K"
    assert game.board.get("f1") == "R"
    assert game.board.get("e1") is None
    assert game.board.get("h1") is None


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
    move = game.make_move(Move("a7", "a8", promotion="Q"))
    assert move.promotion == "Q"
    assert game.board.get("a8") == "Q"


def test_repository_saves_moves():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        repo = GameRepository(db_path=db_path)

        game = repo.create_game(mode="pvp", white_player="Alice")
        repo.join_game(game["id"], "Bob")

        chess = repo.load_chess_game(game["id"])
        move = chess.make_move_uci("e2e4")
        repo.save_move(game["id"], move, "e4", chess.to_state())

        history = repo.get_moves(game["id"])
        assert len(history) == 1
        assert history[0]["uci"] == "e2e4"
        assert history[0]["san"] == "e4"
