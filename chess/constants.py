WHITE = "white"
BLACK = "black"

PIECE_VALUES = {
    "P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 20000,
    "p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 20000,
}

WHITE_PIECES = set("PNBRQK")
BLACK_PIECES = set("pnbrqk")

PROMOTION_PIECES = {"Q", "R", "B", "N"}

FILES = "abcdefgh"
RANKS = "12345678"
