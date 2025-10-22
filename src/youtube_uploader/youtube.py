"""Youtube Uploader"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pydantic import BaseModel, Field, field_validator

from youtube_uploader.utils import resolve_auth_paths

from .exceptions import AuthError, UploadError

# YouTube Data APIのスコープ定義
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)


class YoutubeConfig(BaseModel):
    """YouTubeへの動画アップロードに必要な設定情報

    Args:
        video_path (Path): アップロードする動画ファイルのパス
        title (str): 動画のタイトル
        description (str, optional): 動画の説明文
        tags (list[str], optional): 動画のタグリスト
        category_id (str, optional): 動画のカテゴリID
        selfDeclaredMadeForKids (bool, optional): 子供向けコンテンツかどうかの自己申告
            (デフォルトはFalse)
        privacy_status (str, optional): 動画の公開設定
        publish_at (datetime | None, optional): 予約投稿日時 (Noneの場合は即時公開)
            例：2025-10-20 02:30:00+09:00
    """

    video_path: Path = Field(..., description="アップロードする動画ファイルのパス")
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

    # 予約投稿がprivate以外の場合に警告/エラーを出す
    @field_validator("publish_at")
    @classmethod
    def check_privacy_for_scheduled_post(cls, v, info):
        if v is not None and info.data.get("privacy_status") != "private":
            raise ValueError(
                "予約投稿日時(publish_at)が指定されている場合、"
                "公開設定(privacy_status)は 'private' である必要があります。"
            )
        return v


class YoutubeUploader:
    """YouTube APIを使った認証と動画アップロード処理を担当するコアクラス"""

    def __init__(self, auth_path: Path):
        """指定されたディレクトリに基づきYouTube APIへの認証を行う。

        Args:
            auth_path (Path): 利用する client_secret.jsonが入っているディレクトリのパス

        Raises:
            AuthError: 認証に失敗した場合。

        Examples:
            uploader = YoutubeUploader(~/secrets/my_account)

        Note:
            インスタンス引数はルートでもユーザディレクトリからでも、
            どちらでも可
        """
        # 認証状態とファイルパスを格納するフィールド
        self._youtube_service: Any = None
        self._auth_path = auth_path

        # インスタンス生成時に認証を完了させる
        self._authenticate_service(auth_path)

    def _authenticate_service(self, auth_path: Path):
        """指定パスに基づき認証情報をロードし、APIサービスをインスタンスに設定する。"""
        try:
            # ユーティリティ関数でパスを解決し、ファイルが存在するかチェック
            client_secrets_json_path, token_json_path = resolve_auth_paths(auth_path)
        except FileNotFoundError as e:
            raise e  # client_secrets.json がない場合はそのままエラー
        except Exception as e:
            raise AuthError(f"認証パス取得中に予期せぬエラー: {e}") from e

        # 認証ロジックの実行
        # 内部変数にパスを設定
        self._client_secrets_json_path = client_secrets_json_path
        self._token_json_path = token_json_path

        credentials = None
        # 既存のトークンファイルをチェック
        if self._token_json_path.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(self._token_json_path), SCOPES
                )
            except Exception as e:
                logger.warning(
                    f"トークンファイルの読み込み中にエラーが発生しました: {e} - "
                    "再認証を試みます。"
                )
                # 警告ログを出した上で、credentialsをNoneに戻し、再認証フローに流す
                credentials = None

        # 認証情報が存在しない、または有効でない場合
        if not credentials or not credentials.valid:
            # 期限切れでリフレッシュ可能な場合
            if credentials and credentials.expired and credentials.refresh_token:
                logger.info("認証情報が期限切れのため、リフレッシュします。")

                try:
                    credentials.refresh(Request())
                except Exception as e:
                    # 期限切れリフレッシュ失敗時にAuthErrorを発生
                    raise AuthError(f"トークンのリフレッシュに失敗しました: {e}") from e

            # 初回またはトークンが無効な場合
            else:
                logger.info("認証が必要です。ブラウザを開いてログインしてください。")

                if not self._client_secrets_json_path.exists():
                    # 認証ファイル自体がない場合はここで例外を発生
                    raise FileNotFoundError(
                        f"クライアントシークレットファイルが見つかりません: "
                        f"{self._client_secrets_json_path}"
                    )

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self._client_secrets_json_path), SCOPES
                    )
                    credentials = flow.run_local_server(port=0)
                except Exception as e:
                    # ブラウザ認証フロー失敗時にAuthErrorを発生
                    raise AuthError(
                        f"ブラウザ認証フローでエラーが発生しました: {e}"
                    ) from e

            # 新しい許可証をtoken.jsonに保存
            with open(self._token_json_path, "w") as token:
                token.write(credentials.to_json())
            logger.info(f"新しい認証情報を '{self._token_json_path}' に保存しました。")

        # 認証済みのAPIクライアントを構築して設定
        try:
            self._youtube_service = build("youtube", "v3", credentials=credentials)
        except Exception as e:
            # APIサービス構築失敗時にAuthErrorを発生
            raise AuthError(f"YouTube APIサービスへの接続に失敗しました: {e}") from e

        logger.info("YouTube APIへの接続が完了しました。")

    def upload_video(self, config: YoutubeConfig) -> dict:
        """動画をYouTubeにアップロードする

        Args:
            config (YoutubeConfig): アップロード設定情報

        Returns:
            dict : APIのレスポンス辞書
        """
        # ファイル存在チェック
        # （Pydanticバリデーションを通過しても、実行時にファイルが消える可能性を考慮）
        if not config.video_path.exists():
            raise FileNotFoundError(
                f"指定された動画ファイルが存在しません: {config.video_path}"
            )

        logger.info(f"動画 '{config.title}' のアップロードを開始します...")

        # 動画のメタデータを設定
        body: dict[str, Any] = {
            "snippet": {
                "title": config.title,
                "description": config.description,
                "tags": config.tags,
                "categoryId": config.category_id,
            },
            "status": {
                "privacyStatus": config.privacy_status,
                "selfDeclaredMadeForKids": config.selfDeclaredMadeForKids,
            },
        }

        # 予約投稿日時を設定 (datetimeオブジェクトをISO 8601形式に変換)
        if config.publish_at:
            # configバリデーターによって、publish_atがある場合は
            # privacyStatusがprivateであることが保証されている
            body["status"]["publishAt"] = config.publish_at.isoformat()

        # 動画ファイルのアップロード準備
        media = MediaFileUpload(
            str(config.video_path), chunksize=-1, resumable=True, mimetype="video/*"
        )

        try:
            # APIへの挿入リクエストを構築
            request = self._youtube_service.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            # チャンクアップロードの実行
            response = None
            while response is None:
                # next_chunk()を呼び出し、進捗状況とレスポンスを取得
                status, response = request.next_chunk()
                if status:
                    logger.info(f"アップロード進捗: {int(status.progress() * 100)}%")

            # 結果の検証と戻り値
            if "id" in response:
                video_id = response["id"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"動画のアップロードが完了しました: {video_url}")
                return response
            else:
                logger.error(
                    "動画のアップロードに失敗しました。レスポンスにIDが含まれていません。"
                )
                raise UploadError(
                    "動画のアップロードに失敗しました。レスポンスにIDが含まれていません。"
                )
        except UploadError:
            raise

        except Exception as e:
            logger.error(f"動画のアップロード中にエラーが発生しました: {e}")
            raise UploadError(
                f"動画のアップロード中に予期せぬエラーが発生しました: {e}"
            ) from e
