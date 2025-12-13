"""YouTube APIへの動画アップロードに必要な設定情報のためのデータモデル"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class YoutubeConfig(BaseModel):
    """YouTubeへの動画アップロードに必要な設定情報

    Args:
        video_bytes (bytes): アップロードする動画ファイルのバイナリデータ。
        video_mimetype (str): 動画ファイルのMIMEタイプ (例: 'video/mp4')。
        title (str): 動画のタイトル
        description (str, optional): 動画の説明文
        tags (list[str], optional): 動画のタグリスト
        category_id (str, optional): 動画のカテゴリID
        selfDeclaredMadeForKids (bool, optional): 子供向けコンテンツかどうかの自己申告
            (デフォルトはFalse)
        privacy_status (str, optional): 動画の公開設定
        publish_at (datetime | None, optional): 予約投稿日時 (Noneの場合は即時公開)
            例：2025-10-20 02:30:00+09:00
        thumbnail_bytes (bytes | None, optional): サムネイルファイルのバイナリデータ
            (bytes)
        thumbnail_mimetype (str | None, optional): サムネイルファイルのMIMEタイプ
            (例: 'image/jpeg')
    """

    # --- 動画本体 ---
    video_bytes: bytes = Field(
        ..., description="アップロードする動画ファイルのバイナリデータ (bytes)"
    )
    video_mimetype: str = Field(
        ..., description="動画ファイルのMIMEタイプ (例: 'video/mp4')"
    )

    # --- メタデータ ---
    title: str = Field(..., description="動画のタイトル")
    description: str = Field(default="", description="動画の説明文")
    tags: list[str] = Field(default_factory=list, description="動画のタグリスト")
    category_id: str = Field(default="24", description="動画のカテゴリID")
    selfDeclaredMadeForKids: bool = Field(
        default=False,
        description="子供向けコンテンツかどうかの自己申告 (デフォルトはFalse)",
    )
    privacy_status: Literal["public", "private", "unlisted"] = Field(
        default="private", description="動画の公開設定 (public, private, unlisted)"
    )
    publish_at: datetime | None = Field(
        default=None, description="予約投稿日時 (Noneの場合は即時公開)"
    )

    # --- サムネイル ---
    thumbnail_bytes: bytes | None = Field(
        default=None, description="アップロードするサムネイルのバイナリデータ (bytes)"
    )
    thumbnail_mimetype: str | None = Field(
        default=None, description="サムネイルファイルのMIMEタイプ (例: 'image/jpeg')"
    )

    # 予約投稿がprivate以外の場合に警告/エラーを出す
    @field_validator("publish_at")
    @classmethod
    def check_privacy_for_scheduled_post(cls, v, info):
        """予約投稿がprivate以外の場合に警告/エラーを出す"""
        if v is not None and info.data.get("privacy_status") != "private":
            raise ValueError(
                "予約投稿日時(publish_at)が指定されている場合、"
                "公開設定(privacy_status)は 'private' である必要があります。"
            )
        if v is not None and v.tzinfo is None:
            raise ValueError(
                "予約投稿日時(publish_at)にはタイムゾーン情報(tzinfo)が必要です。"
                "例: datetime.fromisoformat('2025-10-20 02:30:00+09:00')"
            )
        return v

    # サムネイルバイナリがある場合、mimetypeも必須とする
    @field_validator("thumbnail_mimetype")
    @classmethod
    def check_thumbnail_integrity(cls, v, info):
        """サムネイルバイナリがある場合、mimetypeも必須とする"""
        if info.data.get("thumbnail_bytes") is not None and v is None:
            raise ValueError(
                "thumbnail_bytesが指定されている場合、thumbnail_mimetypeも必須です。"
            )
        return v
