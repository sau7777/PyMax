"""Разбор ответа VIDEO_PLAY в VideoRequest.

Регрессии, которые тут закрыты (обе наблюдались вживую):

* **Внешнее видео** (ok.ru и пр.) — MAX присылает ТОЛЬКО ``{"EXTERNAL": "<url>"}``:
  ни ``cache``, ни ``url``. Оба поля были required → ``ValidationError: cache
  Field required``, и видео молча терялось, хотя ссылка была прислана.
* **Посторонний ключ-список** — старый валидатор брал в ``url`` ПЕРВЫЙ попавшийся
  ключ, кроме ``EXTERNAL``/``cache``, включая, например,
  ``{"servers": ["maxvdNNN.okcdn.ru"]}`` → ``ValidationError: url`` (upstream #70).
"""

from pymax.types.domain.attachments.video import VideoRequest


def test_external_only_payload_uses_external_as_url() -> None:
    """Внешнее видео: EXTERNAL — это и есть ссылка, cache отсутствует."""
    url = "https://m.ok.ru/video/123?st.id=17769729690119&scl=1"

    video = VideoRequest(**{"EXTERNAL": url})

    assert video.url == url
    assert video.cache is False
    assert video.external == url


def test_picks_highest_mp4_quality() -> None:
    """Из нескольких качеств выбираем максимальное."""
    video = VideoRequest(
        **{
            "cache": True,
            "MP4_360": "https://cdn/360.mp4",
            "MP4_1080": "https://cdn/1080.mp4",
            "MP4_720": "https://cdn/720.mp4",
        }
    )

    assert video.url == "https://cdn/1080.mp4"


def test_ignores_non_url_keys() -> None:
    """Посторонний ключ со списком не должен попадать в url (upstream #70)."""
    video = VideoRequest(
        **{
            "cache": True,
            "servers": ["maxvd759.okcdn.ru"],
            "MP4_720": "https://cdn/720.mp4",
        }
    )

    assert video.url == "https://cdn/720.mp4"


def test_bool_external_is_not_used_as_url() -> None:
    """external бывает bool-флагом — это не ссылка."""
    video = VideoRequest(
        **{"cache": True, "EXTERNAL": True, "MP4_480": "https://cdn/480.mp4"}
    )

    assert video.url == "https://cdn/480.mp4"
    assert video.external is True


def test_explicit_url_is_kept() -> None:
    """Явный url проходит без изменений."""
    video = VideoRequest(**{"cache": False, "url": "https://cdn/direct.mp4"})

    assert video.url == "https://cdn/direct.mp4"


def test_empty_payload_does_not_raise() -> None:
    """Пустой ответ не должен ронять парсинг."""
    video = VideoRequest()

    assert video.url is None
    assert video.cache is False
