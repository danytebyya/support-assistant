import asyncio

from app.conversation import ConversationStore, expand_follow_up


def test_short_follow_up_inherits_previous_question():
    result = expand_follow_up("а для айфона?", "мне нужно приложение для винды")
    assert "приложение для винды" in result
    assert "для айфона" in result


def test_independent_question_is_not_rewritten():
    message = "Как оплатить подписку Lime HD TV?"
    assert expand_follow_up(message, "Где скачать приложение?") == message


def test_store_remembers_latest_user_turn():
    async def scenario():
        store = ConversationStore()
        await store.add("session", "первый вопрос", "первый ответ")
        await store.add("session", "второй вопрос", "второй ответ")
        return await store.last_user("session")

    assert asyncio.run(scenario()) == "второй вопрос"
