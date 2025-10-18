"""
パッケージの認証ファイルパスや環境変数に関するユーティリティ関数を定義するモジュール。
"""

from pathlib import Path


def get_account_auth_paths(account_name: str) -> tuple[Path, Path]:
    """
    指定されたアカウント名に基づき、認証情報のパスを決定・作成する。

    パス構造: ~/.secrets/youtube-uploader/<account_name>/client_secrets.json

    Raises:
        FileNotFoundError: client_secrets.json が存在しない場合。
    """
    # ベースディレクトリの決定 (.secretsを使用)
    # ディレクトリ名はハイフン区切りに変更: youtube-uploader
    base_dir = Path.home() / ".secrets" / "youtube-uploader" / account_name

    # ディレクトリの作成
    base_dir.mkdir(parents=True, exist_ok=True)

    # ファイルパスの決定
    client_secrets_path = base_dir / "client_secrets.json"
    token_path = base_dir / "token.json"

    # client_secrets.jsonの存在チェック
    if not client_secrets_path.exists():
        # 利用者がファイルを配置すべき場所を伝える
        raise FileNotFoundError(
            f"アカウント '{account_name}' の認証ファイルが見つかりません。 "
            f"'{client_secrets_path}' に配置してください。"
        )

    return client_secrets_path, token_path
