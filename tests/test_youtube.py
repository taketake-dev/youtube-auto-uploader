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

    return client_secrets_path, token_path


@pytest.fixture
def mock_uploader_connected(mocker):
    """connectが成功し、_youtube_serviceがセットされたUploaderインスタンスのモックを返す"""
    mock_youtube_service = MagicMock()

    # next_chunkが最終的に完了したレスポンスを返すように設定
    mock_request = MagicMock()
    mock_request.next_chunk.side_effect = [
        (MagicMock(progress=lambda: 0.5), None),
        (None, {"id": "VIDEO_ID_123", "status": {"privacyStatus": "private"}}),
    ]

    # videos().insert() が mock_request を返すよう設定
    mock_youtube_service.videos().insert.return_value = mock_request

    # Uploaderインスタンスを作成
    uploader = YoutubeUploader()

    # connectメソッド実行時に self._youtube_service を設定する動作を偽装
    mocker.patch.object(
        uploader,
        "connect",
        side_effect=lambda csf, tf: setattr(
            uploader, "_youtube_service", mock_youtube_service
        ),
    )

    # connectを呼び出すことで、uploader._youtube_service が設定される
    uploader.connect(Path("dummy_secrets"), Path("dummy_token"))

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
# 2. connect (認証) ロジックのテスト
# ----------------------------------------------------------------------


@patch("youtube_uploader.youtube.build")
class TestYoutubeUploaderConnect:
    def test_connect_file_not_found(self, mock_build, dummy_files):
        """クライアントシークレットファイルが存在しない場合、FileNotFoundErrorが発生することを検証"""
        client_secrets_path, token_path = dummy_files
        client_secrets_path.unlink()

        uploader = YoutubeUploader()
        with pytest.raises(FileNotFoundError):
            uploader.connect(client_secrets_path, token_path)

    def test_connect_no_token_file_initial_auth(self, mock_build, dummy_files, mocker):
        """トークンファイルがない場合、初回ブラウザ認証が行われ、トークンが保存されることを検証"""
        client_secrets_path, token_path = dummy_files

        # Credentialsと認証フローをモック
        mock_creds = MagicMock(valid=True, to_json=lambda: '{"token": "new"}')
        mock_flow_instance = MagicMock()
        mock_flow_instance.run_local_server.return_value = mock_creds

        mock_flow_patch = mocker.patch(
            "youtube_uploader.youtube.InstalledAppFlow.from_client_secrets_file",
            return_value=mock_flow_instance,
        )

        uploader = YoutubeUploader()
        uploader.connect(client_secrets_path, token_path)

        mock_flow_patch.assert_called_once()
        # 検証 : token.jsonが新しく作成されたこと
        assert token_path.exists()
        # 検証 : APIクライアントが構築されたこと
        mock_build.assert_called_once()
        assert uploader._youtube_service is not None

    @patch("youtube_uploader.youtube.Request")
    def test_connect_token_is_expired(
        self, mock_request, mock_build, dummy_files, mocker
    ):
        """期限切れトークンがある場合、リフレッシュが試行されることを検証"""
        client_secrets_path, token_path = dummy_files

        token_path.write_text('{"token": "expired"}')

        mock_credentials = MagicMock(
            valid=False,
            expired=True,
            refresh_token="exists",
            to_json=lambda: '{"token": "refreshed"}',
        )
        mocker.patch(
            "youtube_uploader.youtube.Credentials.from_authorized_user_file",
            return_value=mock_credentials,
        )

        uploader = YoutubeUploader()
        uploader.connect(client_secrets_path, token_path)

        # 検証 : credentials.refresh() が呼び出されたこと
        mock_credentials.refresh.assert_called_once_with(mock_request())
        # 検証 : APIクライアントが構築されたこと
        mock_build.assert_called_once()
        # 検証 : token.jsonが更新されたこと（to_jsonが呼び出され、書き込まれる）
        assert token_path.exists()


# ----------------------------------------------------------------------
# 3. upload_video ロジックのテスト
# ----------------------------------------------------------------------


def test_upload_video_not_connected():
    """connectが実行されていない場合、Noneを返すことを検証"""
    uploader = YoutubeUploader()
    config = YoutubeConfig(video_path=Path("dummy.mp4"), title="T")

    response = uploader.upload_video(config)

    assert response is None


def test_upload_video_file_not_found(mock_uploader_connected, mocker):
    """動画ファイルが存在しない場合、FileNotFoundErrorを発生させることを検証"""
    uploader, mock_youtube_service = mock_uploader_connected

    # Path.exists() が False を返すようにモック
    mocker.patch.object(Path, "exists", return_value=False)

    config = YoutubeConfig(video_path=Path("non_existent.mp4"), title="Test")

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

    # 検証 : 最終的にAPIのレスポンス辞書が返されたこと
    assert isinstance(response, dict)
    assert response["id"] == "VIDEO_ID_123"

    mock_request.next_chunk.assert_called()
