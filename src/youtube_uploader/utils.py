"""utils

パッケージの認証ファイルパスや環境変数に関するユーティリティ関数を定義するモジュール
"""

from pathlib import Path


def resolve_auth_paths(base_dir: Path) -> tuple[Path, Path]:
    """指定されたベースディレクトリを基に、認証情報のパスを決定

    Args:
        base_dir (Path): client_secret.jsonとtoken.jsonを含むディレクトリ。

    Returns:
        tuple[Path, Path]: (client_secrets_path, token_path)

    Raises:
        FileNotFoundError: client_secret.json が存在しない場合
    """
    # ユーザーが渡したパスを絶対パスに変換し、ディレクトリを自動作成
    resolved_dir = base_dir.expanduser().resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)

    # ファイルパスの決定
    client_secrets_path = resolved_dir / "client_secret.json"
    token_path = resolved_dir / "token.json"

    # 既存のロジックを維持: client_secret.jsonがない場合はエラー
    if not client_secrets_path.exists():
        raise FileNotFoundError(
            f"認証ファイルが見つかりません。推奨パス: '{client_secrets_path}'"
        )

    return client_secrets_path, token_path
