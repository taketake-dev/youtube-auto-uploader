"""
パッケージの認証ファイルパスや環境変数に関するユーティリティ関数を定義するモジュール。
"""

import os
from pathlib import Path


def get_default_auth_paths(base_dir: Path | None = None) -> tuple[Path, Path]:
    """
    クライアントシークレットとトークンファイルのパスを決定します。

    Args:
        base_dir (Path | None): 認証情報を格納するベースディレクトリ。
            Noneの場合、標準の '~/.config/youtube_uploader' を使用します。

    Returns:
        tuple[Path, Path]: (client_secrets_path, token_path)

    Note:
        環境変数 'YOUTUBE_SECRETS_PATH' が設定されている場合、そのパスが優先されます。
    """

    # 1. 環境変数による上書きチェック
    # 環境変数が設定されていれば、それをベースディレクトリとして優先する
    env_path = os.environ.get("YOUTUBE_SECRETS_PATH")
    if env_path:
        config_dir = Path(env_path)
    # 2. デフォルトパスの決定
    elif base_dir is None:
        # OSに依存しないホームディレクトリの取得 (~/.config/youtube_uploader/)
        config_dir = Path.home() / ".config" / "youtube_uploader"
    else:
        config_dir = base_dir

    # ディレクトリが存在しない場合は作成 (初回実行時の利便性向上)
    config_dir.mkdir(parents=True, exist_ok=True)

    # 最終的なファイルパスを決定
    client_secrets_path = config_dir / "client_secrets.json"
    token_path = config_dir / "token.json"

    return client_secrets_path, token_path
