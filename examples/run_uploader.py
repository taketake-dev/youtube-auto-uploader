"""
==================================================
YouTube Uploader パッケージのサンプル実行スクリプト
==================================================

READMEの内容と同一です。
"""

import logging
from datetime import datetime
from pathlib import Path

from youtube_uploader.exceptions import AuthError, UploadError  # カスタム例外
from youtube_uploader.youtube import YoutubeConfig, YoutubeUploader

# ログ設定
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 置き換えてください
TARGET_ACCOUNT_NAME = Path("~/.secrets/youtube-uploader/test-channel")
VIDEO_FILE = Path("./videos/test-video.mp4")
SCHEDULE_TIME = datetime.fromisoformat("2025-10-20 02:30:00+09:00")

# -----------------------------------------------------------
# 1. Uploaderのインスタンス化と認証
# -----------------------------------------------------------

try:
    # インスタンス生成
    # Uploaderの生成時に、アカウント名のパスを解決し、認証が実行されます
    uploader = YoutubeUploader(TARGET_ACCOUNT_NAME)

except FileNotFoundError as e:
    logger.critical(
        f"❌ 認証ファイルが見つかりません。"
        f"パスを確認し、ファイルを配置してください: {e}"
    )
except AuthError as e:
    logger.critical(
        f"❌ 認証エラーが発生しました。"
        f"ブラウザ認証の失敗またはトークン破損の可能性があります: {e}"
    )

# -----------------------------------------------------------
# 2. 設定オブジェクトの作成とアップロード実行
# -----------------------------------------------------------

try:
    # アップロード設定オブジェクトの作成
    config = YoutubeConfig(
        video_path=VIDEO_FILE,
        title="【自動投稿】マイ作品の試作 - 予約デモ",
        description="Pythonスクリプトによる自動アップロード。",
        tags=["Python", "自動化", "ボカロ", "テスト"],
        category_id="24",  # カテゴリIDはYouTubeの公式ドキュメントを参照してください
        privacy_status="private",  # public, private, unlisted があります
        publish_at=SCHEDULE_TIME,  # 設定しない場合は即日公開
    )

    # アップロード実行
    response = uploader.upload_video(config)

    if response:
        logger.info(f"動画ID {response.get('id')} の予約投稿を完了しました。")

except FileNotFoundError as e:
    logger.critical(f"❌ 動画ファイルが見つかりません: {e}")
except UploadError as e:
    logger.critical(f"❌ アップロード中にAPIエラーが発生しました: {e}")
