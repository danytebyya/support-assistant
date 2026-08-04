import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class DownloadAction:
    label: str
    url: str


@dataclass(frozen=True)
class DownloadSource:
    question: str
    url: str


DOWNLOAD_SOURCE = DownloadSource(
    "Скачать Lime HD TV",
    "https://limehd.tv/faq/99999/question/99999",
)


DOWNLOAD_RE = re.compile(
    r"ссылк\w*|\b(?:скачать|установить|загрузить)\b|"
    r"(?:дай|пришли|покажи|нужна|где).{0,30}(?:магазин|маркет)",
    re.I,
)
DOWNLOAD_ALIASES = ("скачать", "установить", "загрузить", "ссылка", "магазин", "маркет")
DOWNLOAD_FUZZY_THRESHOLD = 0.82
IOS_RE = re.compile(r"\b(?:ios|iphone|ipad|app\s*store)\b|айфон|айпад|эпп\s*стор", re.I)
ANDROID_TV_RE = re.compile(r"android\s*tv|андроид\s*тв|приставк", re.I)
ANDROID_RE = re.compile(r"\bandroid\b|андроид|google\s*play|гугл\s*плей", re.I)
WINDOWS_RE = re.compile(r"\bwindows\b|виндовс|компьютер|ноутбук|\bpc\b", re.I)
SMART_TV_RE = re.compile(r"smart\s*tv|смарт\s*тв|телевизор|samsung|самсунг|\blg\b", re.I)
HUAWEI_RE = re.compile(r"huawei|хуавей|appgallery|аппгалер", re.I)
RUSTORE_RE = re.compile(r"rustore|рустор", re.I)

PLATFORM_ALIASES = {
    "ios": ("iphone", "ipad", "ios", "айфон", "айпад"),
    "android_tv": ("androidtv", "андроидтв", "приставка"),
    "windows": ("windows", "виндовс", "виндоус", "винды"),
    "smart_tv": ("smarttv", "смарттв", "телевизор", "samsung", "самсунг"),
    "huawei": ("huawei", "хуавей", "appgallery", "аппгалери"),
    "android": ("android", "андроид"),
}


def detect_platform(message: str) -> str | None:
    text = " ".join(message.lower().split())
    if IOS_RE.search(text):
        return "ios"
    if ANDROID_TV_RE.search(text):
        return "android_tv"
    if WINDOWS_RE.search(text):
        return "windows"
    if SMART_TV_RE.search(text):
        return "smart_tv"
    if HUAWEI_RE.search(text):
        return "huawei"
    if ANDROID_RE.search(text):
        return "android"

    tokens = re.findall(r"[a-zа-яё0-9]+", text)
    best: tuple[float, str | None] = (0.0, None)
    for platform, aliases in PLATFORM_ALIASES.items():
        for token in tokens:
            for alias in aliases:
                score = SequenceMatcher(None, token, alias).ratio()
                if score > best[0]:
                    best = (score, platform)
    return best[1] if best[0] >= 0.72 else None


def is_download_request(message: str) -> bool:
    text = " ".join(message.lower().split())
    if DOWNLOAD_RE.search(text):
        return True
    tokens = re.findall(r"[a-zа-яё]+", text)
    return any(
        SequenceMatcher(None, token, alias).ratio() >= DOWNLOAD_FUZZY_THRESHOLD
        for token in tokens
        for alias in DOWNLOAD_ALIASES
    )


def is_download_platform_follow_up(message: str) -> bool:
    return detect_platform(message) is not None or bool(RUSTORE_RE.search(message))


def download_answer(
    message: str, *, assume_download: bool = False, platform_hint: str | None = None
) -> tuple[str, list[DownloadAction]] | None:
    text = " ".join(message.split())
    if not assume_download and not is_download_request(text):
        return None

    platform = platform_hint or detect_platform(text)

    if platform == "ios":
        return (
            "Скачать Lime HD TV для iPhone или iPad можно в App Store. Нажмите кнопку ниже — откроется официальная страница приложения.",
            [DownloadAction("Открыть в App Store", "https://apps.apple.com/app/id998832333")],
        )
    if RUSTORE_RE.search(text):
        package = "tv.limehd.stb" if platform == "android_tv" else "com.infolink.limeiptv"
        title = "Лайм HD STB" if platform == "android_tv" else "Lime HD TV"
        return (
            f"{title} доступен в RuStore. Нажмите кнопку ниже — откроется официальная карточка приложения.",
            [DownloadAction("Открыть в RuStore", f"https://www.rustore.ru/catalog/app/{package}")],
        )
    if platform == "android_tv":
        return (
            "Для Android TV и приставок доступна отдельная версия Lime HD TV с управлением с пульта.",
            [DownloadAction("Открыть в Google Play", "https://play.google.com/store/apps/details?id=tv.limehd.stb")],
        )
    if platform == "windows":
        return (
            "Версию Lime HD TV для Windows можно скачать на официальной странице. Там находится актуальный установщик.",
            [DownloadAction("Скачать для Windows", "https://play.limehd.tv/limewin")],
        )
    if platform == "smart_tv":
        return (
            "Способ установки зависит от модели телевизора. На официальной странице выберите производителя и следуйте инструкции.",
            [DownloadAction("Открыть инструкции для Smart TV", "https://limehd.tv/instructions")],
        )
    if platform == "huawei":
        return (
            "Откройте официальную страницу Lime HD TV для Android — на ней доступен актуальный вариант установки приложения.",
            [DownloadAction("Открыть страницу загрузки", "https://play.limehd.tv/limehd")],
        )
    if platform == "android":
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
