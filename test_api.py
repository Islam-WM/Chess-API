from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from storage.database import GameRepository


def test_api_pvp_flow():
    with tempfile.TemporaryDirectory() as tmp:
        test_db = Path(tmp) / "api_test.db"

        import api.routes as routes_module

        routes_module.repo = GameRepository(db_path=test_db)
        client = TestClient(app)

        create_resp = client.post(
            "/api/v1/games/pvp",
            json={"white_player": "Alice"},
        )
        assert create_resp.status_code == 200
        game_id = create_resp.json()["id"]

        join_resp = client.post(
            f"/api/v1/games/{game_id}/join",
            json={"player_name": "Bob"},
        )
        assert join_resp.status_code == 200

        move_resp = client.post(
            f"/api/v1/games/{game_id}/move",
            json={"uci": "e2e4", "player_name": "Alice"},
        )
        assert move_resp.status_code == 200
        assert move_resp.json()["move"]["san"] == "e4"

        history_resp = client.get(f"/api/v1/games/{game_id}/moves")
        assert history_resp.status_code == 200
        assert len(history_resp.json()) == 1


def test_api_vs_ai():
    with tempfile.TemporaryDirectory() as tmp:
        test_db = Path(tmp) / "ai_test.db"

        import api.routes as routes_module

        routes_module.repo = GameRepository(db_path=test_db)
        client = TestClient(app)

        create_resp = client.post(
            "/api/v1/games/vs-ai",
            json={
                "player_name": "Max",
                "player_color": "white",
                "ai_engine": "heuristic",
                "ai_depth": 2,
            },
        )
        assert create_resp.status_code == 200
        game_id = create_resp.json()["id"]

        move_resp = client.post(
            f"/api/v1/games/{game_id}/move",
            json={"uci": "e2e4", "player_name": "Max"},
        )
        assert move_resp.status_code == 200

        ai_resp = client.post(f"/api/v1/games/{game_id}/ai-move?depth=2")
        assert ai_resp.status_code == 200
        assert "uci" in ai_resp.json()["move"]
