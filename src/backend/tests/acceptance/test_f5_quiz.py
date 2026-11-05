"""F5 — Culture Quiz (US12–US13)."""
import pytest

from tests.conftest import ac, assert_problem, route

pytestmark = pytest.mark.db


@route("GET", "/api/quizzes")
@ac("AC12.1")
def test_only_published_questions_without_answers(client):
    qs = client.get("/api/quizzes").json()
    assert {q["id"] for q in qs} == {1, 2}
    for q in qs:
        assert "answerIndex" not in q and "explanation" not in q, "không lộ đáp án trước khi trả lời"
        assert 2 <= len(q["options"]) <= 4


@route("GET", "/api/quizzes")
@ac("AC12.1")
@pytest.mark.parametrize("params,expected", [
    ({"country": "JP", "difficulty": "easy"}, {1}),
    ({"category": "etiquette"}, {2}),
    ({"country": "KE"}, set()),
])
def test_quiz_filters(client, params, expected):
    assert {q["id"] for q in client.get("/api/quizzes", params=params).json()} == expected


@route("POST", "/api/quizzes/{id}/attempts")
@ac("AC13.1")
def test_wrong_answer_returns_explanation_and_source(client):
    r = client.post("/api/quizzes/1/attempts", json={"answerIndex": 0})
    assert r.status_code == 200
    res = r.json()
    assert res["correct"] is False and res["answerIndex"] == 1
    assert res["explanation"] and res["sourceIds"] == [1] and res["entryId"] == 1


@route("POST", "/api/quizzes/{id}/attempts")
@ac("AC13.1")
def test_correct_answer(client):
    assert client.post("/api/quizzes/1/attempts", json={"answerIndex": 1}).json()["correct"] is True


@route("POST", "/api/quizzes/{id}/attempts")
@ac("AC12.1")
def test_draft_question_not_answerable(client):
    assert_problem(client.post("/api/quizzes/3/attempts", json={"answerIndex": 0}), 404)


@route("POST", "/api/quizzes/{id}/attempts")
@ac("AC13.1")
def test_answer_index_validated(client):
    assert_problem(client.post("/api/quizzes/1/attempts", json={"answerIndex": 9}), 400)
