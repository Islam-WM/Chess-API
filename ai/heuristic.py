from __future__ import annotations

import random
from typing import Protocol

from chess.constants import PIECE_VALUES, WHITE
from chess.game import ChessGame
from chess.move import Move
from chess.rules import is_in_check


class ChessAI(Protocol):
    def choose_move(self, game: ChessGame) -> Move: ...


def evaluate_board(game: ChessGame) -> int:
    score = 0
    for square, piece in game.state.board.items():
        if piece is None:
            continue
        value = PIECE_VALUES.get(piece, 0)
        if piece.isupper():
            score += value
        else:
            score -= value
    return score


def _move_sort_key(move: Move) -> int:
    if move.promotion:
        return 1000
    if move.is_castling:
        return 50
    if move.captured_piece:
        return PIECE_VALUES.get(move.captured_piece, 0)
    return 0


class HeuristicAI:
    """Minimax-KI mit einfacher Materialbewertung."""

    def __init__(self, depth: int = 3) -> None:
        self.depth = depth

    def choose_move(self, game: ChessGame) -> Move:
        color = game.state.turn
        legal = game.legal_moves()
        if not legal:
            raise ValueError("No legal moves available")

        legal.sort(key=_move_sort_key, reverse=True)

        best_move = legal[0]
        best_score = float("-inf")

        for move in legal:
            score = self._minimax(game, move, self.depth - 1, False, color)
            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def _minimax(
        self,
        game: ChessGame,
        move: Move,
        depth: int,
        maximizing: bool,
        ai_color: str,
    ) -> int:
        test_game = ChessGame.from_state(game.to_state())
        test_game.make_move(move)

        if depth == 0 or test_game.is_game_over():
            raw = evaluate_board(test_game)
            return raw if ai_color == WHITE else -raw

        next_moves = test_game.legal_moves()
        if not next_moves:
            if is_in_check(test_game.board, test_game.state.turn):
                return -99999 if maximizing else 99999
            return 0

        next_moves.sort(key=_move_sort_key, reverse=True)

        if maximizing:
            best = float("-inf")
            for next_move in next_moves:
                score = self._minimax(test_game, next_move, depth - 1, False, ai_color)
                best = max(best, score)
            return best

        best = float("inf")
        for next_move in next_moves:
            score = self._minimax(test_game, next_move, depth - 1, True, ai_color)
            best = min(best, score)
        return best


class RandomAI:
    def choose_move(self, game: ChessGame) -> Move:
        moves = game.legal_moves()
        if not moves:
            raise ValueError("No legal moves available")
        return random.choice(moves)
