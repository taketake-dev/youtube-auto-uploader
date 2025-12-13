# youtube-uploader

現行バージョン: **v5.0.0**

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
- 異なる YouTube アカウントへ動画を投稿

---

## 動作環境

- Linux
- WSL
- Windows
- Mac

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

### ステップ 1: API キーの取得と配置

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成。

2. ライブラリから **YouTube Data API v3** を有効にします。

3. アプリケーションの情報を入力

4. OAuth 2.0 クライアント ID（**デスクトップ アプリケーション**）を作成し、`client_secrets.json` ファイルをダウンロードします。

5. テストユーザーに使用するアカウントのメールアドレスを入れてください。

6. ファイル名を `client_secret.json` に変更してください。

### ステップ 2: 初回認証の実行

コード内で`connect`メソッドを初めて実行すると、自動的にブラウザが開いて Google アカウントの認証を求められます。

認証が完了すると、`token.json`が`client_secret.json`と同じ場所に安全に保存され、次回以降の API 接続は自動化されます。

---

## 🖥️ 基本的な使い方 (サンプル)

認証情報のパスと、アップロード設定（YoutubeConfig）を指定するだけで利用可能です。

```py
"""YouTube Uploader パッケージのサンプル実行スクリプト

このスクリプトは、パッケージの主要な機能（認証、アップロード）をデモンストレーションします。

【実行に必要な準備】
client_secrets.json:
    Google API Consoleからダウンロードした認証情報ファイルを、
    任意のディレクトリに配置してください。
動画ファイル:
    データがなくてもかまいません。
"""

# examples/run_upload.py に移動しました。
```

実行したい場合`examples/run_upload.py`を使用してください。

---

## 🛠️ 開発とテスト

依存関係のインストール
プロジェクトルートで Poetry を使用してください。

```bash
# GitHubから直接インストール
poetry add git+https://github.com/taketake-dev/youtube-uploader.git
```

---

## 📄 ライセンス

本プロジェクトは、**MIT ライセンス**の下で公開されています。詳細については、プロジェクトのルートにある[LICENSE](LICENSE)ファイルを参照してください。
