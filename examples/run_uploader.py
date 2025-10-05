"""
==================================================
YouTube Uploader パッケージのサンプル実行スクリプト
==================================================

このスクリプトは、パッケージの主要な機能（認証、アップロード）をデモンストレーションします。
実行には、以下のファイルが必要です:
1. client_secrets.json: Google API Consoleからダウンロードした認証情報ファイル。
2. test_video.mp4: 任意の動画ファイル (ダミーでも可)。
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# -----------------------------------------------------------
# 1. パッケージのインポート
# -----------------------------------------------------------
# パッケージのcoreモジュールから必要なクラスをインポート
# （パッケージがインストールされている、またはPYTHONPATHが通っている必要があります）
try:
    from youtube_uploader.utils import get_default_auth_paths
    from youtube_uploader.youtube import (
        AuthError,
        UploadError,
        YoutubeConfig,
        YoutubeUploader,
    )
except ImportError:
    print("エラー: youtube_uploader パッケージが見つかりません。")
    print(
        "Poetry環境内で 'poetry run python examples/run_uploader.py' "
        "を実行してください。"
    )
    sys.exit(1)


# -----------------------------------------------------------
# 2. ロギング設定と定数
# -----------------------------------------------------------
# サンプル実行時には、ロガーがコンソールに出力するよう設定する（ベストプラクティス）
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 環境依存の設定ファイルパス（ここでは、リポジトリルートの'secrets'フォルダを想定）
SECRETS_DIR = Path(__file__).parent.parent / "secrets"
CLIENT_SECRETS_FILE = SECRETS_DIR / "client_secrets.json"
TOKEN_FILE = SECRETS_DIR / "token.json"
VIDEO_FILE = SECRETS_DIR / "test_video.mp4"  # アップロードする動画ファイル


def create_dummy_files():
    """認証テストのためにダミーファイルを作成する"""
    if not SECRETS_DIR.exists():
        SECRETS_DIR.mkdir()

    # client_secrets.jsonが存在しない場合、利用者に準備を促す
    if not CLIENT_SECRETS_FILE.exists():
        logger.error(
            "認証ファイルが見つかりません。Google API Consoleからダウンロードし、"
            f"'{CLIENT_SECRETS_FILE}' に配置してください。"
        )
        sys.exit(1)

    # アップロードテストのためにダミー動画を作成
    # （ファイルサイズが0だとアップロードに失敗するため、最低限のデータを入れる）
    if not VIDEO_FILE.exists():
        with open(VIDEO_FILE, "wb") as f:
            f.write(b"\x00" * 1024 * 10)  # 10KBのダミーデータ
        logger.warning(f"アップロード用ダミー動画 '{VIDEO_FILE.name}' を作成しました。")

    # 古いトークンファイルを削除して、認証テストをやり直す
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        logger.info(f"古いトークンファイル '{TOKEN_FILE.name}' を削除しました。")


def run_upload_demo():
    """YoutubeUploaderのデモを実行するメイン関数"""
    logger.info("--- YouTube Uploader サンプル実行開始 ---")

    # 認証ファイルパスの自動取得
    # 引数を指定しない場合、標準の '~/.config/youtube_uploader' を使用します。
    client_secrets_file, token_file = get_default_auth_paths(base_dir=SECRETS_DIR)

    print(f"クライアントシークレット: {client_secrets_file}")
    print(f"トークンファイル: {token_file}")

    if not client_secrets_file.exists():
        print(
            "エラー: クライアントシークレットファイルが存在しません。"
            "推奨パスに配置してください。"
        )
        return

    # 接続 (connectには、ヘルパー関数で取得したパスを渡すだけ)
    uploader = YoutubeUploader()
    uploader.connect(client_secrets_file, token_file)

    # -----------------------------------------------------------
    # 3. 接続（認証）の実行
    # -----------------------------------------------------------
    try:
        uploader = YoutubeUploader()
        logger.info("認証情報をロードし、APIに接続します。")
        uploader.connect(CLIENT_SECRETS_FILE, TOKEN_FILE)
        logger.info("✅ 接続成功。APIクライアントの準備ができました。")

    except FileNotFoundError as e:
        logger.critical(f"致命的なエラー: {e}")
        return
    except AuthError as e:
        logger.critical(f"認証中に予期せぬエラーが発生しました: {e}")
        return

    # -----------------------------------------------------------
    # 4. 設定オブジェクトの作成とアップロード実行
    # -----------------------------------------------------------
    logger.info("\n--- 予約投稿テストを開始 ---")

    # JSTで明日の朝10時に予約投稿する設定を作成
    now = datetime.now(timezone(timedelta(hours=9)))  # JST (UTC+9)
    schedule_time = now + timedelta(days=1)

    try:
        # Pydanticモデルに設定値を渡す
        config = YoutubeConfig(
            video_path=VIDEO_FILE,
            title=f"【自動投稿テスト】ボカロ動画の試作 ({now.strftime('%Y%m%d')})",
            description=(
                "これは、Pythonパッケージを使った自動アップロードのテストです。\n"
                "予約投稿日時: " + schedule_time.isoformat()
            ),
            tags=["Python", "自動化", "ボカロ", "テスト"],
            category_id="10",  # Music カテゴリ
            privacy_status="private",  # 予約投稿は private である必要あり
            publish_at=schedule_time,
        )
        if config.publish_at is not None:
            logger.info(f"予約日時 (ISO): {config.publish_at.isoformat()}")
        else:
            logger.warning("予約日時が設定されていません。")

        # アップロード実行
        response = uploader.upload_video(config)

        if response:
            logger.info(
                "✅ 予約投稿リクエストに成功しました。YouTubeで確認してください。"
            )
        else:
            logger.error("❌ アップロード処理が失敗しました。ログを確認してください。")
    except FileNotFoundError as e:
        # upload_videoメソッド内で発生する動画ファイル不在のエラーを捕捉
        logger.critical(f"❌ 動画ファイルが見つかりません。パスを確認してください: {e}")
    except UploadError as e:
        # カスタム例外のUploadErrorを捕捉
        logger.critical(f"❌ アップロード中に致命的なAPIエラーが発生しました: {e}")
    except Exception as e:
        # 予期せぬシステムエラーなどをキャッチ
        logger.critical(f"致命的なシステムエラーが発生しました: {e}")


if __name__ == "__main__":
    create_dummy_files()
    run_upload_demo()
