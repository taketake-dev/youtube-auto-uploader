from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# テスト対象のモジュールをインポート
from youtube_uploader.youtube import (
    YoutubeConfig,
    YoutubeUploader,
)

# ----------------------------------------------------------------------
# フィクスチャ (テストの準備)
# ----------------------------------------------------------------------


@pytest.fixture
def dummy_files(tmp_path):
    """テスト用に一時的なダミーの認証ファイルパスを作成"""
    client_secrets_path = tmp_path / "client_secrets.json"
    client_secrets_path.write_text('{"client_id": "dummy_id"}')

    token_path = tmp_path / "token.json"

    # ここではファイルを作成せずに、パスだけを返す
    return client_secrets_path, token_path


@pytest.fixture
def mock_uploader_connected(mocker):
    """
    認証が成功した状態（_youtube_serviceがセットされた状態）のUploaderインスタンスのモックを返す。
    内部の認証フローはスキップされます。
    """
    # 1. 内部認証メソッドをモック化し、実処理をスキップ
    mocker.patch.object(YoutubeUploader, "_authenticate_service", autospec=True)

    # 2. 偽のAPIクライアント（動画アップロードメソッドの戻り値を設定）
    mock_youtube_service = MagicMock()
    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = [
        (MagicMock(progress=lambda: 0.5), None),
        (None, {"id": "VIDEO_ID_123", "status": {"privacyStatus": "private"}}),
    ]
    mock_youtube_service.videos().insert.return_value = mock_request

    # 3. Uploaderをインスタンス化
    # （__init__が呼び出され、_authenticate_serviceはモックで成功）
    uploader = YoutubeUploader(Path("dummy_auth_dir"))

    # 4. 手動でモックサービスをセット (インスタンスが使える状態にする)
    uploader._youtube_service = mock_youtube_service

    # MediaFileUploadをモック化
    mocker.patch("youtube_uploader.youtube.MediaFileUpload")

    return uploader, mock_youtube_service


# ----------------------------------------------------------------------
# 1. YoutubeConfig バリデーションのテスト (変更なし)
# ----------------------------------------------------------------------


def test_config_valid_schedule_private():
    """予約投稿とprivate設定が正しく許可されることを検証"""
    config = YoutubeConfig(
        video_path=Path("video.mp4"),
        title="Test",
        privacy_status="private",
        publish_at=datetime.now(),
    )
    assert config.privacy_status == "private"
    assert config.publish_at is not None


def test_config_invalid_schedule_public():
    """予約投稿があるのにpublic設定の場合、ValueErrorが発生することを検証"""
    with pytest.raises(ValueError) as excinfo:
        YoutubeConfig(
            video_path=Path("video.mp4"),
            title="Test",
            privacy_status="public",
            publish_at=datetime.now(),
        )
    assert "公開設定(privacy_status)は 'private' である必要があります" in str(
        excinfo.value
    )


# ----------------------------------------------------------------------
# 2. connect/authenticate ロジックのテスト
# ----------------------------------------------------------------------


# 認証のテストには、buildと、パス解決関数、認証フローをモックする
@patch("youtube_uploader.youtube.build")
@patch("youtube_uploader.youtube.resolve_auth_paths")
class TestYoutubeUploaderConnect:
    # helper: 認証フローをモックし、指定された結果を返す
    def _mock_flow_success(
        self, mocker, token_file, valid=True, expired=False, refreshable=False
    ):
        mock_creds = MagicMock(
            valid=valid,
            expired=expired,
            refresh_token="exists" if refreshable else None,
            to_json=lambda: '{"token": "new"}',
        )
        # Credentials.from_authorized_user_file が返すオブジェクトをモック化
        mocker.patch(
            "youtube_uploader.youtube.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        )
        # 認証フロー (run_local_server) の成功をモック
        mock_flow_instance = MagicMock()
        mock_flow_instance.run_local_server.return_value = mock_creds
        mocker.patch(
            "youtube_uploader.youtube.InstalledAppFlow.from_client_secrets_file",
            return_value=mock_flow_instance,
        )
        return mock_creds

    def test_auth_file_not_found(self, mock_resolve_paths, mock_build, mocker):
        """クライアントシークレットファイルが存在しない場合、FileNotFoundErrorが発生することを検証"""
        # 修正: resolve_auth_pathsがFileNotFoundErrorを発生させるようにモック
        mock_resolve_paths.side_effect = FileNotFoundError

        # __init__を呼び出すと、認証フローが走り、エラーになる
        with pytest.raises(FileNotFoundError):
            YoutubeUploader(Path("non_existent_path"))

        # 認証ロジックが進まなかったため、buildは呼び出されない
        mock_build.assert_not_called()

    def test_auth_no_token_file_initial_auth(
        self, mock_resolve_paths, mock_build, dummy_files, mocker
    ):
        """トークンファイルがない場合、初回ブラウザ認証が行われ、トークンが保存されることを検証"""
        client_secrets_path, token_path = dummy_files

        # 認証パスを返すようモック (token_path.exists()はFalse)
        mock_resolve_paths.return_value = (client_secrets_path, token_path)

        # 認証ロジックが成功するよう内部モックを設定
        self._mock_flow_success(mocker, token_path)

        # 実行: __init__を呼び出す
        uploader = YoutubeUploader(Path("valid_path"))

        # 検証 1: ブラウザ認証フローが実行されたこと
        # (from_client_secrets_fileが呼ばれる)
        mocker.patch(
            "youtube_uploader.youtube.InstalledAppFlow.from_client_secrets_file"
        ).assert_called_once()
        # 検証 2: token.jsonが新しく作成されたこと
        assert token_path.exists()
        # 検証 3: APIクライアントが構築されたこと
        mock_build.assert_called_once()
        assert uploader._youtube_service is not None

    @patch("youtube_uploader.youtube.Request")
    def test_auth_token_is_expired(
        self, mock_request, mock_resolve_paths, mock_build, dummy_files, mocker
    ):
        """期限切れトークンがある場合、リフレッシュが試行されることを検証"""
        client_secrets_path, token_path = dummy_files

        # 認証パスを返すようモック (token_path.exists()はTrue)
        token_path.write_text('{"token": "expired"}')
        mock_resolve_paths.return_value = (client_secrets_path, token_path)

        # 期限切れだがリフレッシュ可能なモックCredentialsを設定
        mock_credentials = self._mock_flow_success(
            mocker, token_path, valid=False, expired=True, refreshable=True
        )

        # 実行: __init__を呼び出す
        YoutubeUploader(Path("expired_token_path"))

        # 検証 1: credentials.refresh() が呼び出されたこと
        mock_credentials.refresh.assert_called_once_with(mock_request())
        # 検証 2: APIクライアントが構築されたこと
        mock_build.assert_called_once()
        # 検証 3: token.jsonが更新されたこと（to_jsonが呼び出され、書き込まれる）
        assert token_path.exists()


# ----------------------------------------------------------------------
# 3. upload_video ロジックのテスト
# ----------------------------------------------------------------------


def test_upload_video_not_connected():
    """__init__の認証をスキップした場合、Noneを返すことを検証"""
    # __init__の認証処理をモックしてスキップする
    with patch.object(YoutubeUploader, "_authenticate_service", autospec=True):
        uploader = YoutubeUploader(Path("dummy"))
        # _youtube_service は None のまま

    config = YoutubeConfig(video_path=Path("dummy.mp4"), title="T")

    response = uploader.upload_video(config)

    assert response is None


def test_upload_video_file_not_found(mock_uploader_connected, mocker):
    """動画ファイルが存在しない場合、FileNotFoundErrorを発生させることを検証"""
    uploader, mock_youtube_service = mock_uploader_connected

    # Path.exists() が False を返すようにモック
    mocker.patch.object(Path, "exists", return_value=False)

    config = YoutubeConfig(video_path=Path("non_existent.mp4"), title="Test")

    # FileNotFoundErrorがraiseされることを期待
    with pytest.raises(FileNotFoundError):
        uploader.upload_video(config)

    # APIはraiseによって呼び出されない
    mock_youtube_service.videos().insert.assert_not_called()


def test_upload_video_correct_body_public(mock_uploader_connected, mocker):
    """公開設定の場合、リクエストボディが正しく構築されることを検証"""
    uploader, mock_youtube_service = mock_uploader_connected
    mock_insert = mock_youtube_service.videos().insert

    mocker.patch.object(Path, "exists", return_value=True)

    config = YoutubeConfig(
        video_path=Path("temp.mp4"),
        title="Test Public Video",
        description="Public Desc",
        privacy_status="public",
        selfDeclaredMadeForKids=True,  # KidsフラグをTrueに設定して検証
    )

    uploader.upload_video(config)

    called_body = mock_insert.call_args.kwargs["body"]

    # 検証
    assert called_body["snippet"]["title"] == "Test Public Video"
    assert called_body["status"]["privacyStatus"] == "public"
    assert called_body["status"]["selfDeclaredMadeForKids"] is True
    assert "publishAt" not in called_body["status"]


def test_upload_video_with_scheduled_publish(mock_uploader_connected, mocker):
    """予約投稿日時が指定された場合、bodyにpublishAtがISO形式で追加されることを検証"""
    uploader, mock_youtube_service = mock_uploader_connected
    mock_insert = mock_youtube_service.videos().insert

    mocker.patch.object(Path, "exists", return_value=True)

    schedule_time = datetime(2026, 1, 1, 10, 0, 0)
    # production codeはタイムゾーンのないISO形式を返すため、期待値もそれに合わせる
    schedule_time_iso = schedule_time.isoformat()

    config = YoutubeConfig(
        video_path=Path("temp.mp4"),
        title="Test Schedule",
        privacy_status="private",
        publish_at=schedule_time,
    )

    uploader.upload_video(config)

    called_body = mock_insert.call_args.kwargs["body"]

    # 検証: publishAtがISO形式で正しく追加されていること
    assert called_body["status"]["privacyStatus"] == "private"
    assert called_body["status"]["publishAt"] == schedule_time_iso


# ----------------------------------------------------------------------
# 4. アップロード完了のテスト
# ----------------------------------------------------------------------


def test_upload_video_completes_and_returns_response(mock_uploader_connected, mocker):
    """アップロードが完了し、APIレスポンスが返されることを検証"""
    uploader, mock_youtube_service = mock_uploader_connected
    mocker.patch.object(Path, "exists", return_value=True)

    config = YoutubeConfig(video_path=Path("temp.mp4"), title="Complete Test")

    # リクエストモックインスタンスを取得
    mock_request = mock_youtube_service.videos().insert.return_value

    response = uploader.upload_video(config)

    # 検証 1: 最終的にAPIのレスポンス辞書が返されたこと
    assert isinstance(response, dict)
    assert response["id"] == "VIDEO_ID_123"

    # 検証 2: next_chunk()が呼び出されたことを確認
    mock_request.next_chunk.assert_called()
