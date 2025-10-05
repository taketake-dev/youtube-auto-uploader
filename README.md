# youtube-uploader

**現在 PyPI には上げていません**

[![Author](https://img.shields.io/badge/Author-taketake--dev-blue.svg)](https://github.com/taketake-dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/youtube-uploader.svg)](https://pypi.org/project/youtube-uploader/)
[![Python Version](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Dependencies](https://img.shields.io/badge/Dependencies-Poetry-60A5FA.svg)](https://python-poetry.org/)
[![Code Style](https://img.shields.io/badge/Linter-Ruff-blueviolet.svg)](https://github.com/astral-sh/ruff)
[![Type Checking](https://img.shields.io/badge/Type_Check-Mypy-orange.svg)](http://mypy-lang.org/)
[![Testing](https://img.shields.io/badge/Tests-Pytest-0A96AA.svg)](https://docs.pytest.org/)
[![Data Validation](https://img.shields.io/badge/Validation-Pydantic-2AA279.svg)](https://pydantic.dev/)
YouTube API を使った認証、設定、および動画の予約投稿を含むアップロード処理を自動化するための、堅牢で再利用可能な Python パッケージです。

## できること

- YouTube へ動画をアップロード
  - 動画のタイトル
  - 動画の説明文
  - 動画のタグリスト
  - 動画のカテゴリ ID
  - 子供向けコンテンツかどうか
  - 動画の公開設定
  - 予約投稿日時

---

## ✨ パッケージの特徴

- **Pydantic による厳密な設定管理:** `YoutubeConfig`クラスにより、入力値の型と制約（予約投稿には`private`が必須など）を API リクエスト前に自動チェックし、実行時のエラーを防ぎます。
- **堅牢な認証フロー:** 初回認証、トークンのリフレッシュ、認証ファイルの管理を自動で行います。
- **カスタム例外によるエラー通知:** 認証失敗時には`AuthError`、アップロード失敗時には`UploadError`など、パッケージ固有のカスタム例外を発生させ、呼び出し側のエラーハンドリングをシンプルにします。
- **クリーンなロギング:** `logging.NullHandler`を使用し、利用側の設定を妨げず、必要な情報のみを正確に伝えます。

---

## 🚀 インストール

本パッケージは Poetry を使用して開発されています。Poetry 環境で利用することを推奨します。

```bash
# Poetry環境に追加
poetry add youtube-uploader
```

---

## 🔑 認証と準備

本パッケージは OAuth 2.0 を使用します。初回接続時にブラウザ経由で認証が必要です。

### ステップ 1: 認証ディレクトリの初期化 (推奨)

最初のステップとして、以下のコマンドを実行し、認証ファイルを配置するディレクトリを自動で作成してください。（任意）

```bash
# 認証ディレクトリを自動作成
poetry run youtube-auth-init
```

このコマンドを実行すると、以下のパスが作成されます。

```bash
~/.config/youtube_uploader/
```

### ステップ 2: API キーの取得と配置

1. Google API Console でプロジェクトを作成し、「YouTube Data API v3」を有効にします。

2. OAuth 2.0 クライアント ID（デスクトップ アプリケーション）を作成し、`client_secrets.json` ファイルをダウンロードします。

3. ダウンロードしたファイルを、以下のデフォルトパスに配置します。

```text
~/.config/youtube_uploader/client_secrets.json
```

（このパスはヘルパー関数 `get_default_auth_paths()`のデフォルト設定に依存します。）
（もしファイル名や場所を変えたい場合は、`connect` メソッドに直接パスを渡してください。）

### ステップ 3: 初回認証の実行

コード内で`connect`メソッドを初めて実行すると、自動的にブラウザが開いて Google アカウントの認証を求められます。

認証が完了すると、`token.json`が`client_secrets.json`と同じ場所に安全に保存され、次回以降の API 接続は自動化されます。

---

## 🖥️ 基本的な使い方 (サンプル)

認証情報のパスと、アップロード設定（YoutubeConfig）を指定するだけで利用可能です。

```py
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from youtube_uploader.youtube import YoutubeUploader, YoutubeConfig, get_default_auth_paths
from youtube_uploader.youtube import AuthError, UploadError # カスタム例外

# ログ設定（INFOレベルで詳細を表示）
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# 認証情報ファイルのパスを自動取得
CLIENT_SECRETS_FILE, TOKEN_FILE = get_default_auth_paths()
VIDEO_FILE = Path("./videos/my_project_final.mp4") # 実際の動画パスに置き換えてください

try:
    # 1. Uploaderのインスタンス化と接続
    uploader = YoutubeUploader()
    uploader.connect(CLIENT_SECRETS_FILE, TOKEN_FILE)

    # 2. 予約投稿の設定 (JSTで翌日10:00に予約)
    jst = timezone(timedelta(hours=9))
    schedule_time = datetime.now(jst) + timedelta(days=1)

    config = YoutubeConfig(
        video_path=VIDEO_FILE,
        title="【自動投稿】マイ作品の試作 - 予約デモ",
        description="Pythonスクリプトによる自動アップロード。",
        tags=["Python", "自動化", "ボカロ", "テスト"],
        category_id="10", # ミュージック
        privacy_status="private",
        publish_at=schedule_time, # datetimeオブジェクトを渡す
    )

    # 3. アップロード実行
    response = uploader.upload_video(config)

    if response:
        print(f"\n[SUCCESS] 動画ID {response.get('id')} の予約投稿を完了しました。")

except FileNotFoundError as e:
    # クライアントシークレットファイルがない場合の処理
    print(f"\n[FATAL ERROR] クライアントシークレットファイルが見つかりません。パスを確認してください: {e}")
except AuthError as e:
    # 認証失敗時の処理
    print(f"\n[FATAL ERROR] 認証エラー: {e}")
except UploadError as e:
    # アップロード中のAPIエラー処理
    print(f"\n[FATAL ERROR] アップロードエラー: {e}")
except Exception as e:
    # その他の予期せぬエラー
    print(f"\n[FATAL ERROR] 予期せぬエラーが発生しました: {e}")
```

詳細は`examples/run_upload.py`を参照してください。

---

## 🛠️ 開発とテスト

依存関係のインストール
プロジェクトルートで Poetry を使用してください。

```bash
poetry install --with dev
```

ユニットテストの実行
外部 API との実際の通信をモック化してテストします。

```bash
poetry run pytest tests/
```

---

## 📄 ライセンス

本プロジェクトは、**MIT ライセンス**の下で公開されています。詳細については、プロジェクトのルートにある[LICENSE](LICENSE)ファイルを参照してください。
