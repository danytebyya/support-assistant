from app.downloads import DOWNLOAD_SOURCE, detect_platform, download_answer, is_download_request


def test_ios_download_link():
    answer, links = download_answer("Дай ссылку на приложение для iPhone")
    assert "App Store" in answer
    assert links[0].url == "https://apps.apple.com/app/id998832333"


def test_android_tv_uses_tv_app():
    _, links = download_answer("Где скачать приложение на Android TV?")
    assert links[0].url.endswith("id=tv.limehd.stb")


def test_short_platform_download_requests_are_detected():
    assert download_answer("Где скачать на Android?") is not None
    assert download_answer("Ссылка для Android TV") is not None
    assert download_answer("Скачать на Windows") is not None


def test_rustore_respects_device_type():
    _, mobile = download_answer("Дай ссылку в RuStore")
    _, tv = download_answer("Скачать Android TV в RuStore")
    assert mobile[0].url.endswith("com.infolink.limeiptv")
    assert tv[0].url.endswith("tv.limehd.stb")


def test_unspecified_device_returns_market_choices():
    _, links = download_answer("Дай ссылку, где скачать приложение Lime HD TV")
    assert {link.label for link in links} >= {"App Store", "Google Play", "Windows"}


def test_greeting_before_download_request_still_returns_markets():
    result = download_answer("Привет, а где можно скачать приложение?")
    assert result is not None
    assert any(link.label == "RuStore" for link in result[1])


def test_regular_support_question_is_not_download_request():
    assert download_answer("Почему не показывает телеканал?") is None


def test_video_resolution_is_not_download_request():
    assert not is_download_request("Что такое 720p?")
    assert download_answer("Что такое 720p?") is None


def test_download_typo_is_detected_without_semantic_false_positives():
    assert is_download_request("Где скочать приложение?")
    assert is_download_request("Как скачаь приложение?")
    assert download_answer("Где скочать приложение?") is not None


def test_restart_program_is_not_mistaken_for_download():
    messages = (
        "10 мин назад началась передача, я хочу начать ее сначала",
        "Как начать просмотр передачи сначала?",
        "Когда начнется следующая передача?",
    )
    assert all(not is_download_request(message) for message in messages)
    assert all(download_answer(message) is None for message in messages)


def test_download_answers_have_faq_source():
    assert DOWNLOAD_SOURCE.url == "https://limehd.tv/faq/99999/question/99999"
    assert DOWNLOAD_SOURCE.question == "Скачать Lime HD TV"


def test_semantic_router_can_force_platform_after_typo_detection():
    answer, links = download_answer(
        "как скачаь прилжоение на айфно?", assume_download=True, platform_hint="ios"
    )
    assert "App Store" in answer
    assert links[0].url == "https://apps.apple.com/app/id998832333"


def test_platform_detection_tolerates_typos_without_guessing_when_absent():
    assert detect_platform("а для айфно?") == "ios"
    assert detect_platform("а для виндоус?") == "windows"
    assert detect_platform("существует приложение Lime HD?") is None


def test_phone_usage_request_detected():
    assert is_download_request("я могу пользоваться с телефона?")
    assert detect_platform("я могу пользоваться с телефона?") == "android"
    answer, links = download_answer("я могу пользоваться с телефона?")
    assert "Google Play" in links[0].label or "Android" in answer
