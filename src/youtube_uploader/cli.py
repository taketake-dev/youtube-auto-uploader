"""
コマンドラインインターフェース (CLI) の初期化関数
"""

import sys

from .utils import get_default_auth_paths


def init_auth_setup():
    """
    認証情報を配置するディレクトリを自動で作成し、ユーザにファイルの配置を促す
    """
    client_secrets_path, _ = get_default_auth_paths()
    config_dir = client_secrets_path.parent

    if client_secrets_path.exists():
        print("✅ 認証ファイルは既に配置されています。")
        print(f"   パス: {client_secrets_path}")
        return

    try:
        # ディレクトリ作成 (mkdir(parents=True, exist_ok=True)が実行される)
        config_dir.mkdir(parents=True, exist_ok=True)

        print("-" * 50)
        print("🔑 YouTube認証ファイルの初期化が必要です。")
        print("-" * 50)
        print(f"1. 認証ディレクトリを自動作成しました: {config_dir}")
        print(
            "2. Google API Consoleから 'client_secrets.json' "
            "をダウンロードしてください。"
        )
        print(
            f"3. ダウンロードしたファイルを '{client_secrets_path.name}' という名前で、"
        )
        print(f"   上記ディレクトリ（{config_dir}）に配置してください。")
        print("\n初期化完了後、メインスクリプトを再度実行してください。")

    except Exception as e:
        print(f"❌ ディレクトリ作成中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_auth_setup()
