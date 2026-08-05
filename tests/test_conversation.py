import asyncio

from app.conversation import ConversationStore, expand_follow_up


def test_short_follow_up_inherits_previous_question():
    result = expand_follow_up("а для айфона?", "мне нужно приложение для винды")
    assert "приложение для винды" in result
    assert "для айфона" in result


def test_independent_question_is_not_rewritten():
    message = "Как оплатить подписку Lime HD TV?"
    assert expand_follow_up(message, "Где скачать приложение?") == message


def test_conjunction_a_question_is_not_rewritten():
    message = "а я могу пользоваться приложением с телеефона?"
    assert expand_follow_up(message, "что такое 480p?") == message


def test_store_remembers_latest_user_turn():
    async def scenario():
        store = ConversationStore()
        await store.add("session", "первый вопрос", "первый ответ")
        await store.add("session", "второй вопрос", "второй ответ")
        return await store.last_user("session")

    assert asyncio.run(scenario()) == "второй вопрос"


def test_store_remembers_accumulated_context():
    async def scenario():
        store = ConversationStore()
        await store.add("session", "а для айфона?", "ответ", context="исходная тема + айфон")
        return await store.last_user("session")

    assert asyncio.run(scenario()) == "исходная тема + айфон"


def test_multiple_follow_ups_do_not_nest_recursively():
    step1 = expand_follow_up("а на ТВ?", "Как скачать?")
    step2 = expand_follow_up("а на Самсунг?", step1)
    assert step2.count("Предыдущий вопрос:") == 1
    assert "Как скачать?" in step2
    assert "а на ТВ?" in step2
    assert "а на Самсунг?" in step2

