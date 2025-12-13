"""YouTube Uploader パッケージのサンプル実行スクリプト"""

import logging
import mimetypes
from datetime import datetime
from pathlib import Path

from youtube_uploader.exceptions import AuthError, UploadError
from youtube_uploader.models import YoutubeConfig
from youtube_uploader.youtube import YoutubeUploader

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 置き換えてください
TARGET_ACCOUNT_NAME = Path("~/.secrets/youtube-uploader/test-channel")

VIDEO_FILE_PATH = Path("./test_assets/test_video.mp4")
THUMBNAIL_FILE_PATH = Path("./test_assets/test_thumbnail.jpg")
SCHEDULE_TIME = datetime.fromisoformat("2026-10-20T02:30:00+09:00")


# コールバック関数を定義
def simple_progress_printer(progress: float):
    """アップロード進捗をCLIで表示するシンプルなコールバック関数"""
    print(f"🔄 アップロード進捗: {progress:.2%} 完了", end="\r", flush=True)


# ファイルデータ取得ユーティリティ
def get_file_data(file_path: Path) -> tuple[bytes, str]:
    """ファイルパスからバイナリデータとMIMEタイプを取得する"""
    if not file_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    mimetype, _ = mimetypes.guess_type(file_path.as_posix())
    if not mimetype:
        raise ValueError(f"MIMEタイプを推定できませんでした: {file_path}")

    return file_path.read_bytes(), mimetype


# -----------------------------------------------------------
# 1. Uploaderのインスタンス化と認証
# -----------------------------------------------------------

try:
    uploader = YoutubeUploader(TARGET_ACCOUNT_NAME)
    uploader.connect()

except FileNotFoundError as e:
    logger.critical(
        f"❌ 認証ファイルが見つかりません。"
        f"パスを確認し、ファイルを配置してください: {e}"
    )
    exit(1)
except AuthError as e:
    logger.critical(
        f"❌ 認証エラーが発生しました。"
        f"ブラウザ認証の失敗またはトークン破損の可能性があります: {e}"
    )
    exit(1)

# -----------------------------------------------------------
# 2. 設定オブジェクトの作成とアップロード実行
# -----------------------------------------------------------

try:
    # ファイルを読み込み、Configに渡す
    video_bytes, video_mimetype = get_file_data(VIDEO_FILE_PATH)

    # サムネイルデータは任意
    thumbnail_bytes, thumbnail_mimetype = None, None
    if THUMBNAIL_FILE_PATH.exists():
        thumbnail_bytes, thumbnail_mimetype = get_file_data(THUMBNAIL_FILE_PATH)

    # アップロード設定オブジェクトの作成
    config = YoutubeConfig(
        video_bytes=video_bytes,
        video_mimetype=video_mimetype,
        title="【自動投稿】マイ作品の試作 - 予約デモ",
        description="Pythonスクリプトによる自動アップロード。",
        tags=["Python", "自動化", "ボカロ", "テスト"],
        category_id="24",
        privacy_status="private",
        publish_at=SCHEDULE_TIME,
        thumbnail_bytes=thumbnail_bytes,
        thumbnail_mimetype=thumbnail_mimetype,
    )

    # アップロード実行
    response = uploader.upload_video(config)

    # 進捗を表示するとアップロード速度が遅くなる可能性があります。
    # 速度と進捗のバランス（10MB）
    # response = uploader.upload_video(
    # config, progress_callback=simple_progress_printer, chunksize=10*1024*1024
    # )

    if response:
        print()  # プログレス表示を確定させるために改行
        logger.info(f"動画ID {response.get('id')} の予約投稿を完了しました。")

except FileNotFoundError as e:
    logger.critical(f"❌ ファイルが見つかりません: {e}")
except UploadError as e:
    logger.critical(f"❌ アップロード中にAPIエラーが発生しました: {e}")
except ValueError as e:
    logger.critical(f"❌ 設定エラーが発生しました: {e}")
