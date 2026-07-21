from __future__ import annotations

from chess.board import Board, coords_to_square, is_black_piece, is_white_piece, piece_color, square_to_coords
from chess.constants import BLACK, WHITE
from chess.move import Move


def _in_bounds(row: int, col: int) -> bool:
    return 0 <= row < 8 and 0 <= col < 8


def _ray_moves(board: Board, start_row: int, start_col: int, directions: list[tuple[int, int]], color: str) -> list[str]:
    moves: list[str] = []
    for dr, dc in directions:
        row, col = start_row + dr, start_col + dc
        while _in_bounds(row, col):
            piece = board.squares[row][col]
            square = coords_to_square(row, col)
            if piece is None:
                moves.append(square)
            else:
                if (color == WHITE and is_black_piece(piece)) or (color == BLACK and is_white_piece(piece)):
                    moves.append(square)
                break
            row += dr
            col += dc
    return moves


def _pseudo_legal_moves_for_piece(board: Board, square: str, color: str) -> list[Move]:
    piece = board.get(square)
    if piece is None or piece_color(piece) != color:
        return []

    row, col = square_to_coords(square)
    piece_type = piece.upper()
    moves: list[Move] = []

    if piece_type == "P":
        direction = -1 if color == WHITE else 1
        start_row = 6 if color == WHITE else 1
        one_row = row + direction

        if _in_bounds(one_row, col) and board.squares[one_row][col] is None:
            to_sq = coords_to_square(one_row, col)
            if one_row in (0, 7):
                for promo in ("Q", "R", "B", "N"):
                    moves.append(Move(square, to_sq, promotion=promo))
            else:
                moves.append(Move(square, to_sq))

            if row == start_row:
                two_row = row + 2 * direction
                if board.squares[two_row][col] is None:
                    moves.append(Move(square, coords_to_square(two_row, col)))

        for dc in (-1, 1):
            capture_row = row + direction
            capture_col = col + dc
            if _in_bounds(capture_row, capture_col):
                target = board.squares[capture_row][capture_col]
                if target and piece_color(target) != color:
                    to_sq = coords_to_square(capture_row, capture_col)
                    if capture_row in (0, 7):
                        for promo in ("Q", "R", "B", "N"):
                            moves.append(Move(square, to_sq, promotion=promo, captured_piece=target))
                    else:
                        moves.append(Move(square, to_sq, captured_piece=target))

    elif piece_type == "N":
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = row + dr, col + dc
            if _in_bounds(nr, nc):
                target = board.squares[nr][nc]
                if target is None or piece_color(target) != color:
                    moves.append(Move(square, coords_to_square(nr, nc), captured_piece=target))

    elif piece_type == "B":
        for to_sq in _ray_moves(board, row, col, [(-1, -1), (-1, 1), (1, -1), (1, 1)], color):
            moves.append(Move(square, to_sq, captured_piece=board.get(to_sq)))

    elif piece_type == "R":
        for to_sq in _ray_moves(board, row, col, [(-1, 0), (1, 0), (0, -1), (0, 1)], color):
            moves.append(Move(square, to_sq, captured_piece=board.get(to_sq)))

    elif piece_type == "Q":
        dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]
        for to_sq in _ray_moves(board, row, col, dirs, color):
            moves.append(Move(square, to_sq, captured_piece=board.get(to_sq)))

    elif piece_type == "K":
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if _in_bounds(nr, nc):
                    target = board.squares[nr][nc]
                    if target is None or piece_color(target) != color:
                        moves.append(Move(square, coords_to_square(nr, nc), captured_piece=target))

    return moves


def _add_castling_moves(
    board: Board,
    color: str,
    castling_rights: dict[str, bool],
    moves: list[Move],
) -> None:
    if is_in_check(board, color):
        return

    king_sq = board.find_king(color)
    row, _ = square_to_coords(king_sq)

    if color == WHITE:
        if castling_rights["white_kingside"]:
            if (
                board.get("f1") is None
                and board.get("g1") is None
                and board.get("h1") == "R"
                and not _is_square_attacked(board, "e1", BLACK)
                and not _is_square_attacked(board, "f1", BLACK)
                and not _is_square_attacked(board, "g1", BLACK)
            ):
                moves.append(Move("e1", "g1", is_castling=True))
        if castling_rights["white_queenside"]:
            if (
                board.get("d1") is None
                and board.get("c1") is None
                and board.get("b1") is None
                and board.get("a1") == "R"
                and not _is_square_attacked(board, "e1", BLACK)
                and not _is_square_attacked(board, "d1", BLACK)
                and not _is_square_attacked(board, "c1", BLACK)
            ):
                moves.append(Move("e1", "c1", is_castling=True))
    else:
        if castling_rights["black_kingside"]:
            if (
                board.get("f8") is None
                and board.get("g8") is None
                and board.get("h8") == "r"
                and not _is_square_attacked(board, "e8", WHITE)
                and not _is_square_attacked(board, "f8", WHITE)
                and not _is_square_attacked(board, "g8", WHITE)
            ):
                moves.append(Move("e8", "g8", is_castling=True))
        if castling_rights["black_queenside"]:
            if (
                board.get("d8") is None
                and board.get("c8") is None
                and board.get("b8") is None
                and board.get("a8") == "r"
                and not _is_square_attacked(board, "e8", WHITE)
                and not _is_square_attacked(board, "d8", WHITE)
                and not _is_square_attacked(board, "c8", WHITE)
            ):
                moves.append(Move("e8", "c8", is_castling=True))


def _add_en_passant_moves(
    board: Board,
    color: str,
    en_passant_target: str | None,
    moves: list[Move],
) -> None:
    if en_passant_target is None:
        return

    ep_row, ep_col = square_to_coords(en_passant_target)
    direction = -1 if color == WHITE else 1
    pawn = "P" if color == WHITE else "p"

    for dc in (-1, 1):
        row = ep_row - direction
        col = ep_col + dc
        if _in_bounds(row, col) and board.squares[row][col] == pawn:
            from_sq = coords_to_square(row, col)
            captured_row = ep_row + direction
            captured_sq = coords_to_square(captured_row, ep_col)
            captured = board.get(captured_sq)
            moves.append(
                Move(
                    from_sq,
                    en_passant_target,
                    is_en_passant=True,
                    captured_piece=captured,
                )
            )


def _is_square_attacked(board: Board, square: str, by_color: str) -> bool:
    row, col = square_to_coords(square)

    pawn_dir = 1 if by_color == WHITE else -1
    for dc in (-1, 1):
        pr, pc = row + pawn_dir, col + dc
        if _in_bounds(pr, pc):
            piece = board.squares[pr][pc]
            if piece and piece.upper() == "P" and piece_color(piece) == by_color:
                return True

    for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
        nr, nc = row + dr, col + dc
        if _in_bounds(nr, nc):
            piece = board.squares[nr][nc]
            if piece and piece.upper() == "N" and piece_color(piece) == by_color:
                return True

    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        nr, nc = row + dr, col + dc
        while _in_bounds(nr, nc):
            piece = board.squares[nr][nc]
            if piece:
                if piece_color(piece) == by_color and piece.upper() in ("B", "Q"):
                    return True
                break
            nr += dr
            nc += dc

    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = row + dr, col + dc
        while _in_bounds(nr, nc):
            piece = board.squares[nr][nc]
            if piece:
                if piece_color(piece) == by_color and piece.upper() in ("R", "Q"):
                    return True
                break
            nr += dr
            nc += dc

    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if _in_bounds(nr, nc):
                piece = board.squares[nr][nc]
                if piece and piece.upper() == "K" and piece_color(piece) == by_color:
                    return True

    return False


def is_in_check(board: Board, color: str) -> bool:
    king_sq = board.find_king(color)
    return _is_square_attacked(board, king_sq, opponent_color(color))


def opponent_color(color: str) -> str:
    return BLACK if color == WHITE else WHITE


def apply_move(board: Board, move: Move) -> None:
    piece = board.get(move.from_square)
    board.set(move.from_square, None)

    if move.is_en_passant:
        ep_row, ep_col = square_to_coords(move.to_square)
        capture_row = ep_row + (1 if piece_color(piece) == WHITE else -1)
        board.set(coords_to_square(capture_row, ep_col), None)

    if move.is_castling:
        if move.to_square[0] == "g":
            rook_from, rook_to = ("h1", "f1") if piece == "K" else ("h8", "f8")
        else:
            rook_from, rook_to = ("a1", "d1") if piece == "K" else ("a8", "d8")
        rook = board.get(rook_from)
        board.set(rook_from, None)
        board.set(rook_to, rook)

    if move.promotion:
        promoted = move.promotion if piece_color(piece) == WHITE else move.promotion.lower()
        board.set(move.to_square, promoted)
    else:
        board.set(move.to_square, piece)


def generate_pseudo_legal_moves(
    board: Board,
    color: str,
    castling_rights: dict[str, bool],
    en_passant_target: str | None,
) -> list[Move]:
    moves: list[Move] = []
    for square in board.all_squares():
        piece = board.get(square)
        if piece and piece_color(piece) == color:
            moves.extend(_pseudo_legal_moves_for_piece(board, square, color))

    _add_castling_moves(board, color, castling_rights, moves)
    _add_en_passant_moves(board, color, en_passant_target, moves)
    return moves


def generate_legal_moves(
    board: Board,
    color: str,
    castling_rights: dict[str, bool],
    en_passant_target: str | None,
) -> list[Move]:
    legal: list[Move] = []
    for move in generate_pseudo_legal_moves(board, color, castling_rights, en_passant_target):
        test_board = board.copy()
        apply_move(test_board, move)
        if not is_in_check(test_board, color):
            legal.append(move)
    return legal


def update_castling_rights_after_move(
    castling_rights: dict[str, bool],
    move: Move,
    piece: str,
) -> dict[str, bool]:
    rights = dict(castling_rights)

    if piece == "K":
        rights["white_kingside"] = False
        rights["white_queenside"] = False
    elif piece == "k":
        rights["black_kingside"] = False
        rights["black_queenside"] = False
    elif piece == "R" and move.from_square == "a1":
        rights["white_queenside"] = False
    elif piece == "R" and move.from_square == "h1":
        rights["white_kingside"] = False
    elif piece == "r" and move.from_square == "a8":
        rights["black_queenside"] = False
    elif piece == "r" and move.from_square == "h8":
        rights["black_kingside"] = False

    if move.to_square == "a1":
        rights["white_queenside"] = False
    elif move.to_square == "h1":
        rights["white_kingside"] = False
    elif move.to_square == "a8":
        rights["black_queenside"] = False
    elif move.to_square == "h8":
        rights["black_kingside"] = False

    return rights


def compute_en_passant_target(move: Move, piece: str) -> str | None:
    if piece is None or piece.upper() != "P":
        return None
    from_row, from_col = square_to_coords(move.from_square)
    to_row, to_col = square_to_coords(move.to_square)
    if abs(from_row - to_row) == 2 and from_col == to_col:
        ep_row = (from_row + to_row) // 2
        return coords_to_square(ep_row, from_col)
    return None
