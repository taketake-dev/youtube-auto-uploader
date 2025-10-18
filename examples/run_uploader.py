"""
==================================================
YouTube Uploader パッケージのサンプル実行スクリプト
==================================================

このスクリプトは、パッケージの主要な機能（認証、アップロード）をデモンストレーションします。

実行には、以下のファイルが必要です:
1. 認証情報: Google API Consoleからダウンロードした client_secrets.json を、
   ~/.secrets/youtube-uploader/[アカウント名]/ に配置してください。
   （例: ~/.secrets/youtube-uploader/my-channel-name/client_secrets.json）
2. test-video.mp4: 任意の動画ファイル (ダミーでも可)。
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# -----------------------------------------------------------
# 1. パッケージのインポート
# -----------------------------------------------------------
try:
    from youtube_uploader.exceptions import AuthError, UploadError
    from youtube_uploader.utils import get_account_auth_paths
    from youtube_uploader.youtube import YoutubeConfig, YoutubeUploader
except ImportError:
    print(
        "エラー: パッケージのインポートに失敗しました。"
        "Poetry環境を確認してください: {e}"
    )
    print(
        "Poetry環境内で 'poetry run python examples/run_uploader.py' "
        "を実行してください。"
    )
    sys.exit(1)


# -----------------------------------------------------------
# 2. ロギング設定と定数
# -----------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 決めたチャンネル独自のディレクトリ名を指定
TARGET_ACCOUNT_NAME = "my-channel-name"  # ここを各自のアカウント名に変更してください
# ユーティリティ関数を使って、ターゲットとなるディレクトリパスを取得
CLIENT_SECRETS_FILE, TOKEN_FILE = get_account_auth_paths(TARGET_ACCOUNT_NAME)
VIDEO_FILE = Path("./videos/test-video.mp4")  # 認証情報と同じフォルダの動画を想定


def create_dummy_files():
    """認証とアップロードに必要なファイルが存在しない場合に、作成を促す"""
    # ユーティリティ関数が既にディレクトリを作成していることを前提とする

    # client_secrets.jsonが存在しない場合、利用者に準備を促す
    if not CLIENT_SECRETS_FILE.exists():
        logger.error(
            "認証ファイルが見つかりません。Google API Consoleからダウンロードし、"
            f"'{CLIENT_SECRETS_FILE}' に配置してください。"
        )
        sys.exit(1)

    # アップロードテストのためにダミー動画を作成
    if not VIDEO_FILE.exists():
        with open(VIDEO_FILE, "wb") as f:
            f.write(b"\x00" * 1024 * 10)  # 10KBのダミーデータ
        logger.warning(f"アップロード用ダミー動画 '{VIDEO_FILE.name}' を作成しました。")

    # トークンファイルの確認をしたい場合は、以下のコメントアウトを外してください
    # 古いトークンファイルを削除して、認証テストをやり直す
    # if TOKEN_FILE.exists():
    #     TOKEN_FILE.unlink()
    #     logger.info(f"古いトークンファイル '{TOKEN_FILE.name}' を削除しました。")


def run_upload_demo():
    """YoutubeUploaderのデモを実行するメイン関数"""
    logger.info("--- YouTube Uploader サンプル実行開始 ---")

    logger.info(f"ターゲットアカウント: {TARGET_ACCOUNT_NAME}")
    logger.info(f"認証情報パス: {CLIENT_SECRETS_FILE}")

    # -----------------------------------------------------------
    # 3. Uploaderのインスタンス化と認証（最も重要な変更点）
    # -----------------------------------------------------------
    try:
        # Uploaderを生成した瞬間に認証が実行されます。
        uploader = YoutubeUploader(TARGET_ACCOUNT_NAME)
        logger.info("✅ API接続成功。")

    except FileNotFoundError as e:
        # get_account_auth_paths内で発生する client_secrets.json 不在のエラーを捕捉
        logger.critical(f"❌ 認証に必要なファイルが見つかりません: {e}")
        return
    except AuthError as e:
        # 認証フロー、トークンリフレッシュ、APIサービス構築の失敗を捕捉
        logger.critical(
            f"❌ 認証エラーが発生しました。トークン破損の可能性があります: {e}"
        )
        return
    except Exception as e:
        logger.critical(f"予期せぬシステムエラーが発生しました: {e}")
        return

    # -----------------------------------------------------------
    # 4. 設定オブジェクトの作成とアップロード実行
    # -----------------------------------------------------------
    logger.info("\n--- 予約投稿テストを開始 ---")

    # JSTで明日の朝10時に予約投稿する設定を作成
    now = datetime.now(timezone(timedelta(hours=9)))
    schedule_time = now + timedelta(days=1)

    try:
        # Pydanticモデルに設定値を渡す
        config = YoutubeConfig(
            video_path=VIDEO_FILE,  # 認証情報と同じフォルダの動画パス
            title=(
                f"【投稿テスト】({TARGET_ACCOUNT_NAME})からの予約投稿"
                f"({now.strftime('%Y%m%d')})"
            ),
            description="Pythonパッケージを使った自動アップロードのデモ。",
            tags=["Python", "自動化", "ボカロ", "テスト"],
            privacy_status="private",
            publish_at=schedule_time,
        )

        # アップロード実行
        response = uploader.upload_video(config)

        if response:
            logger.info(
                f"✅ 予約投稿リクエストに成功しました。動画ID: {response.get('id')}"
            )
        else:
            # 内部でUploadErrorが発生し、Noneが返された場合
            logger.error(
                "❌ アップロード処理が失敗しました。APIエラーの可能性があります。"
            )

    except FileNotFoundError as e:
        # 動画ファイルが見つからないエラーを捕捉
        logger.critical(f"❌ 動画ファイルが見つかりません: {e}")
    except UploadError as e:
        # カスタム例外のUploadErrorを捕捉
        logger.critical(f"❌ アップロード中に致命的なAPIエラーが発生しました: {e}")
    except Exception as e:
        logger.critical(f"予期せぬシステムエラーが発生しました: {e}")


if __name__ == "__main__":
    # 実行前に、まずは認証ディレクトリを作成・確認するヘルパー関数を呼び出す
    # これにより、TARGET_ACCOUNT_NAMEのディレクトリが確実に作成される
    get_account_auth_paths(TARGET_ACCOUNT_NAME)

    create_dummy_files()
    run_upload_demo()
