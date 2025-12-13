"""YouTube Uploader

Note:
  2018.02.16 時点で有効なカテゴリの一覧
    1 映画・アニメーション
    2 自動車・乗り物
    10 音楽
    15 ペット・動物
    17 スポーツ
    19 旅行・イベント
    20 ゲーム
    22 人物・ブログ
    23 コメディ
    24 エンターテイメント
    25 ニュース・政治
    26 ハウツー・スタイル
    27 教育
    28 サイエンス・テクノロジー
"""

import io
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from googleapiclient.http import MediaIoBaseUpload  # type: ignore

from .exceptions import AuthError, UploadError
from .models import YoutubeConfig
from .utils import resolve_auth_paths

# YouTube Data APIのスコープ定義
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)


class YoutubeUploader:
    """YouTube APIを使った認証と動画アップロード処理を担当するコアクラス

    このクラスは、API認証情報の管理、トークンのリフレッシュ、および
    動画/サムネイルのアップロード処理を抽象化する

    Methods:
        - connect(): YouTube APIへの認証と接続を確立します
        - upload_video(config: YoutubeConfig): 指定された設定で動画をアップロードします
    """

    def __init__(self, auth_path: Path):
        """指定されたディレクトリに基づきYouTube APIへの認証を行う。

        Args:
            auth_path (Path): 利用する client_secret.jsonが入っているディレクトリのパス

        Examples:
            uploader = YoutubeUploader(Path("~/secrets/my_account"))
            uploader.connect()

        Note:
            インスタンス引数はルートでもユーザディレクトリからでも、
            どちらでも可
        """
        # 認証状態とファイルパスを格納するフィールド
        self._youtube_service: Any = None
        self._auth_path = auth_path

        # 内部で利用するパスのフィールドを初期化
        self._client_secrets_json_path: Path | None = None
        self._token_json_path: Path | None = None

    def connect(self) -> None:
        """指定パスに基づき認証情報をロードし、APIサービスをインスタンスに設定する

        Raises:
            AuthError: 認証に失敗した場合
        """
        if self._youtube_service is not None:
            logger.info("既にYouTube APIへの接続が完了しています。")
            return

        try:
            # ユーティリティ関数でパスを解決し、ファイルが存在するかチェック
            (client_secrets_json_path, token_json_path) = resolve_auth_paths(
                self._auth_path
            )
        except FileNotFoundError as e:
            # client_secrets.json がない場合はそのままエラー
            raise e
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

    def upload_video(
        self,
        config: YoutubeConfig,
        progress_callback: Callable[[float], None] | None = None,
        chunksize: int = -1,
    ) -> dict:
        """動画をYouTubeにアップロードする

        Args:
            config (YoutubeConfig): アップロード設定情報
            progress_callback (Callable[[float], None] | None, optional):
                アップロード進捗を通知するコールバック関数
                引数には進捗率（0.0 から 1.0）が渡される
            chunksize (int, optional):
                アップロードのチャンクサイズ（バイト単位）
                デフォルトは-1（全体を一度にアップロード、最速だが進捗表示なし）
                進捗を表示したい場合は10 * 1024 * 1024などの値を指定

        Returns:
            dict : APIのレスポンス辞書

        Raises:
            UploadError: アップロード中にAPIエラーが発生した場合
            AuthError: APIに接続されていない場合
        """
        if self._youtube_service is None:
            raise AuthError(
                "YouTube APIに接続されていません。"
                "connect() メソッドを呼び出してください。"
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
            body["status"]["publishAt"] = config.publish_at.isoformat()

        # MediaIoBaseUploadは、io.BytesIOを受け取る
        media = MediaIoBaseUpload(
            io.BytesIO(config.video_bytes),
            chunksize=chunksize,
            resumable=True,
            mimetype=config.video_mimetype,
        )

        try:
            # APIへの挿入リクエストを構築
            request = self._youtube_service.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            # チャンクアップロードの実行
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = status.progress()  # 進捗率を取得 (0.0 から 1.0)

                    # --- 進捗コールバックを呼び出す ---
                    if progress_callback:
                        progress_callback(progress)
                    else:
                        # コールバックが指定されていない場合のみログに出力
                        logger.info(f"アップロード進捗: {int(progress * 100)}%")

            # 結果の検証と戻り値
            if "id" in response:
                video_id = response["id"]

                # サムネイルのアップロード処理
                self._upload_thumbnail(video_id, config)

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

    def _upload_thumbnail(self, video_id: str, config: YoutubeConfig) -> None:
        """指定された動画IDにサムネイル画像をアップロードする

        Args:
            video_id (str): 対象となるYouTube動画のID
            config (YoutubeConfig): アップロード設定情報
        """
        if config.thumbnail_bytes is None or config.thumbnail_mimetype is None:
            return  # データがなければスキップ

        logger.info("サムネイルのアップロードを開始します...")

        media = MediaIoBaseUpload(
            io.BytesIO(config.thumbnail_bytes),
            chunksize=-1,
            resumable=True,
            mimetype=config.thumbnail_mimetype,
        )

        try:
            self._youtube_service.thumbnails().set(
                videoId=video_id, media_body=media
            ).execute()

            logger.info("サムネイルのアップロードが完了しました。")

        except HttpError as e:
            # --- 権限がない可能性の処理 ---
            if e.resp.status == 403:  # 403 Forbidden は権限がない可能性が高い
                logger.critical(
                    "❌ サムネイルアップロード権限エラー: "
                    "YouTubeアカウントが電話番号で認証されていない可能性があります。"
                )
                logger.critical(f"詳細なAPIエラーメッセージ: {e.content.decode()}")
            else:
                # その他のAPIエラーはUploadErrorとして再発生させる
                logger.error(
                    f"サムネイルアップロード中に予期せぬAPIエラーが発生しました: {e}"
                )
                # サムネイルアップロード失敗は致命的ではないため、例外を再発生させない
                pass
        except Exception as e:
            logger.error(f"サムネイルアップロード中に予期せぬエラーが発生しました: {e}")
            # サムネイルアップロード失敗は致命的ではないため、例外を再発生させない
            pass
