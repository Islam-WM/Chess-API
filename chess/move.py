from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Move:
    from_square: str
    to_square: str
    promotion: str | None = None
    is_castling: bool = False
    is_en_passant: bool = False
    captured_piece: str | None = None

    def to_uci(self) -> str:
        uci = f"{self.from_square}{self.to_square}"
        if self.promotion:
            uci += self.promotion.lower()
        return uci

    @classmethod
    def from_uci(cls, uci: str) -> Move:
        if len(uci) not in (4, 5):
            raise ValueError(f"Invalid UCI move: {uci}")
        from_sq = uci[:2]
        to_sq = uci[2:4]
        promotion = uci[4].upper() if len(uci) == 5 else None
        return cls(from_square=from_sq, to_square=to_sq, promotion=promotion)

    def to_san(self, piece: str | None, is_capture: bool, is_check: bool, is_checkmate: bool) -> str:
        if self.is_castling:
            if self.to_square[0] == "g":
                return "O-O"
            return "O-O-O"

        piece_char = piece.upper() if piece else ""
        if piece_char == "P":
            san = ""
            if is_capture:
                san = f"{self.from_square[0]}x{self.to_square}"
            else:
                san = self.to_square
        else:
            san = piece_char
            if is_capture:
                san += f"x{self.to_square}"
            else:
                san += self.to_square

        if self.promotion:
            san += f"={self.promotion}"

        if is_checkmate:
            san += "#"
        elif is_check:
            san += "+"

        return san


@dataclass
class GameState:
    board: dict[str, str | None]
    turn: str
    castling_rights: dict[str, bool] = field(
        default_factory=lambda: {
            "white_kingside": True,
            "white_queenside": True,
            "black_kingside": True,
            "black_queenside": True,
        }
    )
    en_passant_target: str | None = None
    halfmove_clock: int = 0
    fullmove_number: int = 1
    status: str = "active"
    winner: str | None = None
    result_reason: str | None = None

    def to_fen(self) -> str:
        from chess.board import Board

        board = Board.from_dict(self.board)
        rights = ""
        if self.castling_rights["white_kingside"]:
            rights += "K"
        if self.castling_rights["white_queenside"]:
            rights += "Q"
        if self.castling_rights["black_kingside"]:
            rights += "k"
        if self.castling_rights["black_queenside"]:
            rights += "q"
        if not rights:
            rights = "-"
        ep = self.en_passant_target or "-"
        turn_char = "w" if self.turn == "white" else "b"
        return (
            f"{board.to_fen_board()} {turn_char} {rights} {ep} "
            f"{self.halfmove_clock} {self.fullmove_number}"
        )
