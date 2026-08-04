from scripts.update_faq import parse


def test_json_ld_parser():
    html = '''<script type="application/ld+json">{"@type":"FAQPage","mainEntity":[
    {"@type":"Question","name":"Как войти?","acceptedAnswer":{"text":"Откройте профиль."}}
    ]}</script>'''
    assert parse(html)[0]["question"] == "Как войти?"


def test_details_parser():
    html = "<details><summary>Вопрос</summary><p>Ответ</p></details>"
    result = parse(html)
    assert result[0]["answer"] == "Ответ"

