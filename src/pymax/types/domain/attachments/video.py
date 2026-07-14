from typing import Any, Literal

from pydantic import Field, model_validator

from pymax.types.domain.base import CamelModel

from .enums import AttachmentType


class VideoAttachment(CamelModel):
    """Видео-вложение сообщения.

    Используйте этот тип для входящих видео в ``Message.attaches``. Временный
    URL для просмотра можно получить через ``client.get_video_by_id``.

    Example:
        .. code-block:: python

           for attach in message.attaches:
               if isinstance(attach, VideoAttachment):
                   video = await client.get_video_by_id(
                       message.chat_id,
                       message.id,
                       attach.video_id,
                   )

    :ivar height: Высота видео.
    :vartype height: int
    :ivar width: Ширина видео.
    :vartype width: int
    :ivar video_id: ID видео.
    :vartype video_id: int
    :ivar duration: Длительность видео.
    :vartype duration: int | None
    :ivar preview_data: Данные превью.
    :vartype preview_data: bytes
    :ivar type: Тип вложения.
    :vartype type: Literal[AttachmentType.VIDEO]
    :ivar thumbnail: URL миниатюры.
    :vartype thumbnail: str
    :ivar token: Токен видео.
    :vartype token: str
    :ivar video_type: Код типа видео в Max.
    :vartype video_type: int
    """

    height: int
    width: int
    video_id: int
    duration: int | None = None
    preview_data: bytes
    type: Literal[AttachmentType.VIDEO] = Field(alias="_type")
    thumbnail: str
    token: str
    video_type: int


class VideoRequest(CamelModel):
    """Данные для просмотра видео-вложения.

    :ivar external: Признак или URL внешнего источника видео.
    :vartype external: str | bool | None
    :ivar cache: Использовать ли кеш. Отсутствует у внешнего видео.
    :vartype cache: bool
    :ivar url: URL видео (прямой, либо внешний из ``EXTERNAL``).
    :vartype url: str | None
    """

    external: str | bool | None = Field(default=None, alias="EXTERNAL")
    # cw-патч: у ВНЕШНЕГО видео MAX присылает только {"EXTERNAL": "<url>"} — ни
    # `cache`, ни `url` в ответе нет. Оба поля были required → ValidationError
    # («cache Field required»), и видео молча терялось (наблюдали на проде 14.07.2026).
    cache: bool = False
    url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def unwrap_dynamic_url(cls, value: Any) -> Any:
        """Нормализует URL видео в поле ``url``.

        MAX отдаёт прямой URL под ДИНАМИЧЕСКИМ ключом качества (``MP4_1080`` и т.п.),
        а у внешнего видео — только под ``EXTERNAL``.

        :param value: Значение, переданное в валидатор модели.
        :type value: Any
        :returns: Данные запроса видео или исходное значение.
        :rtype: Any
        """
        if not isinstance(value, dict) or "url" in value:
            return value

        # 1) Прямой URL: берём максимальное доступное MP4-качество.
        # Строгая проверка ключа (MP4_<число>) и типа значения — иначе в `url`
        # попадал ЛЮБОЙ посторонний ключ, включая списки вроде
        # {"servers": ["maxvdNNN.okcdn.ru"]} → ValidationError (upstream issue #70).
        mp4: list[tuple[int, str]] = []
        for key, url in value.items():
            if not isinstance(key, str) or not isinstance(url, str):
                continue
            normalized = key.upper()
            if not normalized.startswith("MP4_"):
                continue
            try:
                quality = int(normalized.removeprefix("MP4_"))
            except ValueError:
                continue
            if quality > 0:
                mp4.append((quality, url))
        if mp4:
            return {**value, "url": max(mp4, key=lambda item: item[0])[1]}

        # 2) Legacy-ключ прямого URL.
        legacy = value.get("dynamicUrl", value.get("dynamic_url"))
        if isinstance(legacy, str) and legacy:
            return {**value, "url": legacy}

        # 3) cw-патч: ВНЕШНЕЕ видео (ok.ru и пр.) — сам EXTERNAL и есть ссылка.
        # Без этого url остаётся None, и видео не скачивается, хотя URL был прислан.
        # (`external` бывает и bool-флагом — тогда это не ссылка, пропускаем.)
        external = value.get("EXTERNAL")
        if isinstance(external, str) and external:
            return {**value, "url": external}

        return value
