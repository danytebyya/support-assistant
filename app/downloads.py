import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadAction:
    label: str
    url: str


DOWNLOAD_RE = re.compile(
    r"ссылк\w*|\b(?:скачать|установить|загрузить)\b|"
    r"(?:дай|пришли|покажи|нужна|где).{0,30}(?:магазин|маркет)",
    re.I,
)
IOS_RE = re.compile(r"\b(?:ios|iphone|ipad|app\s*store)\b|айфон|айпад|эпп\s*стор", re.I)
ANDROID_TV_RE = re.compile(r"android\s*tv|андроид\s*тв|приставк", re.I)
ANDROID_RE = re.compile(r"\bandroid\b|андроид|google\s*play|гугл\s*плей", re.I)
WINDOWS_RE = re.compile(r"\bwindows\b|виндовс|компьютер|ноутбук|\bpc\b", re.I)
SMART_TV_RE = re.compile(r"smart\s*tv|смарт\s*тв|телевизор|samsung|самсунг|\blg\b", re.I)
HUAWEI_RE = re.compile(r"huawei|хуавей|appgallery|аппгалер", re.I)
RUSTORE_RE = re.compile(r"rustore|рустор", re.I)


def download_answer(message: str) -> tuple[str, list[DownloadAction]] | None:
    text = " ".join(message.split())
    if not DOWNLOAD_RE.search(text):
        return None

    if IOS_RE.search(text):
        return (
            "Скачать Lime HD TV для iPhone или iPad можно в App Store. Нажмите кнопку ниже — откроется официальная страница приложения.",
            [DownloadAction("Открыть в App Store", "https://apps.apple.com/app/id998832333")],
        )
    if RUSTORE_RE.search(text):
        package = "tv.limehd.stb" if ANDROID_TV_RE.search(text) else "com.infolink.limeiptv"
        title = "Лайм HD STB" if ANDROID_TV_RE.search(text) else "Lime HD TV"
        return (
            f"{title} доступен в RuStore. Нажмите кнопку ниже — откроется официальная карточка приложения.",
            [DownloadAction("Открыть в RuStore", f"https://www.rustore.ru/catalog/app/{package}")],
        )
    if ANDROID_TV_RE.search(text):
        return (
            "Для Android TV и приставок доступна отдельная версия Lime HD TV с управлением с пульта.",
            [DownloadAction("Открыть в Google Play", "https://play.google.com/store/apps/details?id=tv.limehd.stb")],
        )
    if WINDOWS_RE.search(text):
        return (
            "Версию Lime HD TV для Windows можно скачать на официальной странице. Там находится актуальный установщик.",
            [DownloadAction("Скачать для Windows", "https://play.limehd.tv/limewin")],
        )
    if SMART_TV_RE.search(text):
        return (
            "Способ установки зависит от модели телевизора. На официальной странице выберите производителя и следуйте инструкции.",
            [DownloadAction("Открыть инструкции для Smart TV", "https://limehd.tv/instructions")],
        )
    if HUAWEI_RE.search(text):
        return (
            "Откройте официальную страницу Lime HD TV для Android — на ней доступен актуальный вариант установки приложения.",
            [DownloadAction("Открыть страницу загрузки", "https://play.limehd.tv/limehd")],
        )
    if ANDROID_RE.search(text):
        return (
            "Скачать Lime HD TV для телефона или планшета Android можно в Google Play.",
            [DownloadAction("Открыть в Google Play", "https://play.google.com/store/apps/details?id=com.infolink.limeiptv")],
        )

    return (
        "Выберите устройство — откроется подходящая официальная страница установки Lime HD TV.",
        [
            DownloadAction("App Store", "https://apps.apple.com/app/id998832333"),
            DownloadAction("Google Play", "https://play.google.com/store/apps/details?id=com.infolink.limeiptv"),
            DownloadAction("RuStore", "https://www.rustore.ru/catalog/app/com.infolink.limeiptv"),
            DownloadAction("Android TV", "https://play.google.com/store/apps/details?id=tv.limehd.stb"),
            DownloadAction("Windows", "https://play.limehd.tv/limewin"),
        ],
    )
