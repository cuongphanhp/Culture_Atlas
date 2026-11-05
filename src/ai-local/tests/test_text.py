from ai_local.text import clean_for_speech, tidy_transcript


def test_clean_for_speech():
    md = "## Gợi ý\n- Trao quà bằng **hai tay** [c1]\n- Tránh bộ 4 món [c2][c3]\nXem [JNTO](https://japan.travel)."
    assert clean_for_speech(md) == "Gợi ý. Trao quà bằng hai tay. Tránh bộ 4 món. Xem JNTO."


def test_tidy_transcript():
    assert tidy_transcript("  Ở NHẬT   BẢN QUÀ ") == "Ở nhật bản quà"
    assert tidy_transcript("") == ""
