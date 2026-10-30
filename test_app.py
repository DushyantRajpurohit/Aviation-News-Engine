import sqlite3

import pytest

import demo_engine
import server


@pytest.mark.parametrize("text, expected", [
    # "United" must not match inside other words, or lose to a stronger signal
    ("The reunited crew flew a fighter for the air force.", "Defence"),
    ("The airline added a scheduled passenger route.", "Commercial"),
    # The category with the most hits wins, not the first one listed
    ("An airline moved cargo by freight, handling logistics.", "Cargo"),
    ("Nothing relevant here.", "General"),
])
def test_assign_category(text, expected):
    assert demo_engine.assign_category(text) == expected


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DB_NAME", str(tmp_path / "news.db"))
    monkeypatch.setattr(server, "IMAGE_FOLDER", str(tmp_path / "images"))
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "real.jpg").write_bytes(b"x")
    return server.app.test_client()


def add_article(image_path, body="Short body."):
    conn = sqlite3.connect(server.DB_NAME)
    conn.execute("""CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY, url TEXT UNIQUE, heading TEXT,
                    category TEXT, body_text TEXT, image_path TEXT, date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("INSERT INTO articles (url, heading, category, body_text, image_path) VALUES (?, 'H', 'General', ?, ?)",
                 (f"https://example.com/{image_path}", body, image_path))
    conn.commit()
    conn.close()


def test_missing_database_gives_empty_feed(client):
    response = client.get("/api/news")
    assert response.status_code == 200
    assert response.get_json() == []


@pytest.mark.parametrize("stored, expected", [
    ("demo_images/real.jpg", "/images/real.jpg"),
    ("demo_images\\real.jpg", "/images/real.jpg"),
    ("demo_images/gone.jpg", None),
    ("Image Too Small", None),
    ("No Image", None),
])
def test_only_real_image_files_get_a_url(client, stored, expected):
    add_article(stored)
    assert client.get("/api/news").get_json()[0]["image_url"] == expected


def test_preview_is_only_marked_truncated_when_it_is(client):
    add_article("a", body="Short body.")
    add_article("b", body="x" * 300)
    bodies = {a["original_url"][-1]: a["body"] for a in client.get("/api/news").get_json()}
    assert bodies["a"] == "Short body."
    assert bodies["b"] == "x" * 200 + "..."
