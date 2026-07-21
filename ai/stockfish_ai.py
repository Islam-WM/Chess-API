from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from chess.game import ChessGame
from chess.move import Move

if TYPE_CHECKING:
    from ai.heuristic import ChessAI


class StockfishAI:
    """Stockfish-Integration über UCI-Protokoll (optional)."""

    def __init__(self, stockfish_path: str | None = None, skill_level: int = 10) -> None:
        self.stockfish_path = stockfish_path or self._find_stockfish()
        self.skill_level = skill_level
        self._process: subprocess.Popen[str] | None = None

    @staticmethod
    def _find_stockfish() -> str | None:
        return shutil.which("stockfish")

    @property
    def is_available(self) -> bool:
        return self.stockfish_path is not None

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._process is None:
            if not self.stockfish_path:
                raise RuntimeError("Stockfish not found on system PATH")
            self._process = subprocess.Popen(
                [self.stockfish_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._send("uci")
            self._wait_for("uciok")
            self._send(f"setoption name Skill Level value {self.skill_level}")
            self._send("isready")
            self._wait_for("readyok")
        return self._process

    def _send(self, command: str) -> None:
        proc = self._ensure_process()
        assert proc.stdin is not None
        proc.stdin.write(command + "\n")
        proc.stdin.flush()

    def _read_line(self) -> str:
        proc = self._ensure_process()
        assert proc.stdout is not None
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("Stockfish process ended unexpectedly")
        return line.strip()

    def _wait_for(self, token: str) -> None:
        while True:
            line = self._read_line()
            if token in line:
                return

    def choose_move(self, game: ChessGame) -> Move:
        fen = game.to_state().to_fen()
        self._send(f"position fen {fen}")
        self._send("go depth 12")

        best_move_uci = None
        while True:
            line = self._read_line()
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] != "(none)":
                    best_move_uci = parts[1]
                break

        if not best_move_uci:
            raise ValueError("Stockfish returned no move")

        return Move.from_uci(best_move_uci)

    def close(self) -> None:
        if self._process:
            try:
                self._send("quit")
            except Exception:
                pass
            self._process.terminate()
            self._process = None


def get_ai(engine: str, depth: int = 3) -> ChessAI:
    from ai.heuristic import HeuristicAI, RandomAI

    if engine == "stockfish":
        stockfish = StockfishAI()
        if stockfish.is_available:
            return stockfish
        return HeuristicAI(depth=depth)
    if engine == "random":
        return RandomAI()
    return HeuristicAI(depth=depth)
