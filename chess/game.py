from __future__ import annotations

from chess.board import Board
from chess.constants import BLACK, WHITE
from chess.move import GameState, Move
from chess.rules import (
    apply_move,
    compute_en_passant_target,
    generate_legal_moves,
    is_in_check,
    opponent_color,
    update_castling_rights_after_move,
)


class ChessGame:
    def __init__(self, state: GameState | None = None) -> None:
        self.state = state or GameState(
            board=Board().to_dict(),
            turn=WHITE,
        )

    @property
    def board(self) -> Board:
        return Board.from_dict(self.state.board)

    def legal_moves(self) -> list[Move]:
        return generate_legal_moves(
            self.board,
            self.state.turn,
            self.state.castling_rights,
            self.state.en_passant_target,
        )

    def is_game_over(self) -> bool:
        return self.state.status != "active"

    def _update_status(self) -> None:
        legal = self.legal_moves()
        in_check = is_in_check(self.board, self.state.turn)

        if legal:
            return

        if in_check:
            self.state.status = "checkmate"
            self.state.winner = opponent_color(self.state.turn)
            self.state.result_reason = "checkmate"
        else:
            self.state.status = "stalemate"
            self.state.winner = None
            self.state.result_reason = "stalemate"

    def make_move(self, move: Move) -> Move:
        if self.is_game_over():
            raise ValueError("Game is already over")

        legal = self.legal_moves()
        matching = [m for m in legal if self._moves_equal(m, move)]
        if not matching:
            raise ValueError(f"Illegal move: {move.to_uci()}")

        actual_move = matching[0]
        board = self.board
        piece = board.get(actual_move.from_square)
        if piece is None:
            raise ValueError("No piece on source square")

        captured = actual_move.captured_piece
        if actual_move.is_en_passant:
            captured = "p" if self.state.turn == WHITE else "P"

        apply_move(board, actual_move)
        self.state.board = board.to_dict()

        self.state.castling_rights = update_castling_rights_after_move(
            self.state.castling_rights,
            actual_move,
            piece,
        )
        self.state.en_passant_target = compute_en_passant_target(actual_move, piece)

        if piece.upper() == "P" or captured:
            self.state.halfmove_clock = 0
        else:
            self.state.halfmove_clock += 1

        if self.state.turn == BLACK:
            self.state.fullmove_number += 1

        self.state.turn = opponent_color(self.state.turn)
        self._update_status()

        if self.state.halfmove_clock >= 100:
            self.state.status = "draw"
            self.state.result_reason = "fifty_move_rule"

        actual_move.captured_piece = captured
        return actual_move

    def make_move_uci(self, uci: str) -> Move:
        return self.make_move(Move.from_uci(uci))

    @staticmethod
    def _moves_equal(a: Move, b: Move) -> bool:
        return (
            a.from_square == b.from_square
            and a.to_square == b.to_square
            and (a.promotion or "").upper() == (b.promotion or "").upper()
        )

    def to_state(self) -> GameState:
        return self.state

    @classmethod
    def from_state(cls, state: GameState) -> ChessGame:
        return cls(state=state)

    def get_check_status(self) -> bool:
        return is_in_check(self.board, self.state.turn)
