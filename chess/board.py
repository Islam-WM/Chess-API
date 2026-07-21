from __future__ import annotations

from copy import deepcopy

from chess.constants import BLACK, BLACK_PIECES, FILES, RANKS, WHITE, WHITE_PIECES


def square_to_coords(square: str) -> tuple[int, int]:
    file_idx = FILES.index(square[0])
    rank_idx = 8 - int(square[1])
    return rank_idx, file_idx


def coords_to_square(row: int, col: int) -> str:
    return f"{FILES[col]}{8 - row}"


def is_white_piece(piece: str | None) -> bool:
    return piece is not None and piece in WHITE_PIECES


def is_black_piece(piece: str | None) -> bool:
    return piece is not None and piece in BLACK_PIECES


def piece_color(piece: str | None) -> str | None:
    if piece is None:
        return None
    if piece in WHITE_PIECES:
        return WHITE
    return BLACK


def opponent(color: str) -> str:
    return BLACK if color == WHITE else WHITE


class Board:
    def __init__(self, squares: list[list[str | None]] | None = None) -> None:
        if squares is None:
            self.squares = self._initial_board()
        else:
            self.squares = deepcopy(squares)

    @staticmethod
    def _initial_board() -> list[list[str | None]]:
        empty = [[None for _ in range(8)] for _ in range(8)]
        back_rank_white = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        back_rank_black = ["r", "n", "b", "q", "k", "b", "n", "r"]
        for col in range(8):
            empty[7][col] = back_rank_white[col]
            empty[6][col] = "P"
            empty[1][col] = "p"
            empty[0][col] = back_rank_black[col]
        return empty

    def get(self, square: str) -> str | None:
        row, col = square_to_coords(square)
        return self.squares[row][col]

    def set(self, square: str, piece: str | None) -> None:
        row, col = square_to_coords(square)
        self.squares[row][col] = piece

    def copy(self) -> Board:
        return Board(self.squares)

    def find_king(self, color: str) -> str:
        target = "K" if color == WHITE else "k"
        for row in range(8):
            for col in range(8):
                if self.squares[row][col] == target:
                    return coords_to_square(row, col)
        raise ValueError(f"King not found for {color}")

    def all_squares(self) -> list[str]:
        return [coords_to_square(r, c) for r in range(8) for c in range(8)]

    def to_fen_board(self) -> str:
        rows: list[str] = []
        for row in self.squares:
            fen_row = ""
            empty_count = 0
            for piece in row:
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count:
                        fen_row += str(empty_count)
                        empty_count = 0
                    fen_row += piece
            if empty_count:
                fen_row += str(empty_count)
            rows.append(fen_row)
        return "/".join(rows)

    def to_ascii(self) -> str:
        lines = ["  a b c d e f g h"]
        for row_idx, row in enumerate(self.squares):
            rank = 8 - row_idx
            cells = []
            for piece in row:
                cells.append(piece if piece else ".")
            lines.append(f"{rank} " + " ".join(cells))
        return "\n".join(lines)

    def to_dict(self) -> dict[str, str | None]:
        return {square: self.get(square) for square in self.all_squares()}

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> Board:
        board = cls()
        for square, piece in data.items():
            board.set(square, piece)
        return board
