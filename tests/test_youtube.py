"""youtube.py用のユニットテスト

現在使用不可
v5に対応していません
"""

# from datetime import datetime
# from pathlib import Path
# from unittest.mock import MagicMock, patch

# import pytest

# # カスタム例外のインポート
# from youtube_uploader.exceptions import AuthError, UploadError

# # テスト対象のモジュールをインポート
# from youtube_uploader.youtube import (
#     YoutubeConfig,
#     YoutubeUploader,
# )

# # ----------------------------------------------------------------------
# # フィクスチャ (テストの準備)
# # ----------------------------------------------------------------------


# @pytest.fixture
# def dummy_files(tmp_path):
#     """テスト用に一時的なダミーの認証ファイルパスを作成"""
#     # 認証情報を配置するディレクトリ
#     auth_dir = tmp_path / "test-channel"
#     auth_dir.mkdir()

#     client_secrets_path = auth_dir / "client_secrets.json"
#     # client_secrets.json が存在しない場合のテストのために、ここでは作成しない

#     token_path = auth_dir / "token.json"

#     # ここではファイルを作成せずに、パスだけを返す (必要に応じてテスト内で作成する)
#     return client_secrets_path, token_path


# @pytest.fixture
# def mock_uploader_connected(mocker):
#     """
#     認証が成功した状態（_youtube_serviceがセットされた状態）のUploaderインスタンスのモックを返す。
#     内部の認証フローはスキップされます。
#     """
#     # 1. 内部認証メソッドをモック化し、実処理をスキップ
#     mocker.patch.object(YoutubeUploader, "_authenticate_service", autospec=True)

#     # 2. 偽のAPIクライアント（動画アップロードメソッドの戻り値を設定）
#     mock_youtube_service = MagicMock()

#     # next_chunkのサイドエフェクト：
#     # 1. 進行状況を返す (Noneではないのでアップロードが継続)
#     # 2. 最終レスポンスを返す
#     mock_request = MagicMock()
#     mock_request.next_chunk.side_effect = [
#         (MagicMock(progress=lambda: 0.5), None),
#         (None, {"id": "VIDEO_ID_123", "status": {"privacyStatus": "private"}}),
#     ]
#     mock_youtube_service.videos().insert.return_value = mock_request

#     # 3. Uploaderをインスタンス化（__init__が呼び出されるが、認証はモックでスキップ）
#     uploader = YoutubeUploader(Path("dummy_auth_dir"))

#     # 4. 手動でモックサービスをセット (インスタンスが使える状態にする)
#     uploader._youtube_service = mock_youtube_service

#     # MediaFileUploadをモック化（アップロード時の依存関係）
#     mocker.patch("youtube_uploader.youtube.MediaFileUpload")

#     return uploader, mock_youtube_service


# # ----------------------------------------------------------------------
# # 1. YoutubeConfig バリデーションのテスト
# # ----------------------------------------------------------------------


# def test_config_valid_schedule_private():
#     """予約投稿とprivate設定が正しく許可されることを検証"""
#     aware_dt = datetime.fromisoformat("2025-10-22T20:00:00+09:00")

#     config = YoutubeConfig(
#         video_path=Path("video.mp4"),
#         title="Test",
#         privacy_status="private",
#         publish_at=aware_dt,
#     )
#     assert config.privacy_status == "private"
#     assert config.publish_at is not None


# def test_config_invalid_schedule_public():
#     """予約投稿があるのにprivate以外の設定の場合、ValueErrorが発生することを検証"""
#     # メッセージの検証を外し、ValueErrorが発生することのみを確認します。
#     with pytest.raises(ValueError):
#         YoutubeConfig(
#             video_path=Path("video.mp4"),
#             title="Test",
#             # private以外
#             privacy_status="public",
#             publish_at=datetime.now(),
#         )
#     # 以前あったメッセージ検証は、テストの脆さを避けるため削除しました。


# def test_config_rejects_naive_datetime_for_publish_at():
#     """予約投稿日時がタイムゾーン情報(tzinfo)を持たない場合、ValueErrorが発生することを検証"""
#     # Naive datetime (タイムゾーンなし)
#     naive_dt = datetime(2025, 12, 31, 23, 59, 59)

#     # ValueErrorが発生することのみを確認 (動作保証)
#     with pytest.raises(ValueError):
#         YoutubeConfig(
#             video_path=Path("video.mp4"),
#             title="Test",
#             privacy_status="private",
#             publish_at=naive_dt,
#         )


# def test_config_aware_datetime_is_allowed():
#     """予約投稿日時がタイムゾーン情報を持つ場合、正しく許可されることを検証"""
#     # Aware datetime (タイムゾーンあり)
#     # タイムゾーン情報を持つISO形式の文字列から生成します（推奨される書き方）。
#     aware_dt = datetime.fromisoformat("2025-12-31T23:59:59+09:00")

#     config = YoutubeConfig(
#         video_path=Path("video.mp4"),
#         title="Test",
#         privacy_status="private",
#         publish_at=aware_dt,
#     )
#     # 値が正しく設定され、タイムゾーン情報を持っていることを確認
#     assert config.publish_at == aware_dt

#     assert config.publish_at is not None
#     assert config.publish_at.tzinfo is not None


# # ----------------------------------------------------------------------
# # 2. connect/authenticate ロジックのテスト
# # ----------------------------------------------------------------------


# # 認証のテストには、buildと、パス解決関数、認証フローをモックする
# @patch("youtube_uploader.youtube.build")
# @patch("youtube_uploader.youtube.resolve_auth_paths")
# class TestYoutubeUploaderConnect:
#     # helper: ブラウザ認証フローのモック（成功時）
#     # Credentials.from_authorized_user_file のモックはここでは行わない
#     def _mock_flow_success(self, mocker, valid=True, expired=False, refreshable=False):
#         """ブラウザ認証成功時のモックを設定し、CredentialsとInstalledAppFlowのモックを返す"""
#         mock_creds = MagicMock(
#             valid=valid,
#             expired=expired,
#             refresh_token="exists" if refreshable else None,
#             to_json=lambda: '{"token": "new"}',
#         )

#         # 認証フロー (run_local_server) の成功をモック
#         mock_flow_instance = MagicMock()
#         mock_flow_instance.run_local_server.return_value = mock_creds

#         # InstalledAppFlow.from_client_secrets_file をモックし、
#         # そのモックオブジェクトを変数に保持
#         mock_flow_factory = mocker.patch(
#             "youtube_uploader.youtube.InstalledAppFlow.from_client_secrets_file",
#             return_value=mock_flow_instance,
#         )
#         # ブラウザ認証で取得される credentials モックと、
#         # フローのファクトリメソッドのモックオブジェクトを返す
#         return mock_creds, mock_flow_factory

#     # helper: 認証フローのモック（失敗時）
#     def _mock_flow_fail(self, mocker):
#         mock_flow_instance = MagicMock()
#         mock_flow_instance.run_local_server.side_effect = Exception(
#             "Browser Auth Error"
#         )
#         mocker.patch(
#             "youtube_uploader.youtube.InstalledAppFlow.from_client_secrets_file",
#             return_value=mock_flow_instance,
#         )

#     def test_auth_client_secrets_file_not_found(
#         self, mock_resolve_paths, mock_build, mocker, dummy_files
#     ):
#         """クライアントシークレットファイルが存在しない場合、FileNotFoundErrorが発生することを検証"""
#         client_secrets_path, token_path = dummy_files

#         # resolve_auth_paths がパスを返すようモック
#         # (中での存在チェックをシミュレーション)
#         mock_resolve_paths.return_value = (client_secrets_path, token_path)

#         # token.json も client_secrets.json も存在しない状態をシミュレーション
#         assert not client_secrets_path.exists()
#         assert not token_path.exists()

#         # __init__ を呼び出すと、
#         # resolve_auth_paths の中で FileNotFoundError が発生するはず
#         with pytest.raises(FileNotFoundError):
#             YoutubeUploader(Path("non_existent_path"))

#         mock_build.assert_not_called()

#     def test_auth_no_token_file_initial_auth_success(
#         self, mock_resolve_paths, mock_build, dummy_files, mocker
#     ):
#         """トークンファイルがない場合、初回ブラウザ認証が行われ、トークンが保存されることを検証"""
#         client_secrets_path, token_path = dummy_files
#         client_secrets_path.write_text(
#             '{"client_id": "dummy_id"}'
#         )  # シークレットファイルは必要

#         # 認証パスを返すようモック (token_path.exists()はFalse)
#         mock_resolve_paths.return_value = (client_secrets_path, token_path)

#         # 認証ロジックが成功するよう内部モックを設定
#         mock_creds, mock_flow_factory = self._mock_flow_success(mocker)

#         # 実行: __init__を呼び出す
#         uploader = YoutubeUploader(Path("valid_path"))

#         # 検証 1: ブラウザ認証フローが実行されたこと
#         # (from_client_secrets_fileが呼ばれる)
#         mock_flow_factory.assert_called_once()

#         # 検証 2: token.jsonが新しく作成されたこと
#         # (ファイルは一時ディレクトリに作成される)
#         assert token_path.exists()

#         # 検証 3: APIクライアントが構築されたこと
#         mock_build.assert_called_once()
#         assert uploader._youtube_service is not None

#     def test_auth_token_file_corrupted_falls_back_to_browser_auth(
#         self, mock_resolve_paths, mock_build, dummy_files, mocker
#     ):
#         """トークンファイルが破損している場合、警告を出し再認証フローに移行することを検証"""
#         client_secrets_path, token_path = dummy_files
#         client_secrets_path.write_text('{"client_id": "dummy_id"}')
#         token_path.write_text("this is not json")  # 意図的に破損させる

#         mock_resolve_paths.return_value = (client_secrets_path, token_path)

#         # from_authorized_user_file が失敗して、browser auth が成功するパスをモック
#         mock_creds_failure = MagicMock(side_effect=Exception("Corrupted Token"))
#         mocker.patch(
#             "youtube_uploader.youtube.Credentials.from_authorized_user_file",
#             mock_creds_failure,
#         )

#         # ブラウザ認証成功のモックを設定 (フォールバック先の成功を保証)
#         mock_creds, mock_flow_factory = self._mock_flow_success(mocker)

#         # 実行: __init__を呼び出す
#         uploader = YoutubeUploader(Path("corrupted_token_path"))

#         # 検証 1: from_authorized_user_file が呼び出され、失敗したこと
#         mock_creds_failure.assert_called_once()

#         # 検証 2: ブラウザ認証フローが実行されたこと
#         mock_flow_factory.assert_called_once()

#         # 検証 3: APIクライアントが構築されたこと
#         mock_build.assert_called_once()
#         assert uploader._youtube_service is not None

#     @patch("youtube_uploader.youtube.Request")
#     def test_auth_token_is_expired_refresh_success(
#         self, mock_request, mock_resolve_paths, mock_build, dummy_files, mocker
#     ):
#         """期限切れトークンがある場合、リフレッシュが成功することを検証"""
#         client_secrets_path, token_path = dummy_files
#         client_secrets_path.write_text('{"client_id": "dummy_id"}')
#         token_path.write_text('{"token": "expired"}')  # トークンファイルが存在する状態
#         mock_resolve_paths.return_value = (client_secrets_path, token_path)

#         # 期限切れだがリフレッシュ可能なモックCredentialsを設定
#         mock_credentials, _ = self._mock_flow_success(
#             mocker, valid=False, expired=True, refreshable=True
#         )

#         # from_authorized_user_file がこの期限切れの Credentials を返すよう設定
#         mocker.patch(
#             "youtube_uploader.youtube.Credentials.from_authorized_user_file",
#             return_value=mock_credentials,
#         )

#         # 実行: __init__を呼び出す
#         YoutubeUploader(Path("expired_token_path"))

#         # 検証 1: credentials.refresh() が呼び出されたこと
#         mock_credentials.refresh.assert_called_once_with(mock_request())

#         # 検証 2: APIクライアントが構築されたこと
#         mock_build.assert_called_once()

#         # 検証 3: token.jsonが更新されたこと（to_jsonが呼び出され、書き込まれる）
#         assert token_path.exists()

#     @patch("youtube_uploader.youtube.Request")
#     def test_auth_refresh_failed_raises_error(
#         self, mock_request, mock_resolve_paths, mock_build, dummy_files, mocker
#     ):
#         """期限切れトークンのリフレッシュに失敗した場合、AuthErrorが発生することを検証"""
#         client_secrets_path, token_path = dummy_files
#         client_secrets_path.write_text('{"client_id": "dummy_id"}')
#         token_path.write_text('{"token": "expired"}')
#         mock_resolve_paths.return_value = (client_secrets_path, token_path)

#         # 期限切れだがリフレッシュ可能なモックCredentialsを設定
#         mock_credentials, _ = self._mock_flow_success(
#             mocker, valid=False, expired=True, refreshable=True
#         )

#         # from_authorized_user_file がこの期限切れの Credentials を返すよう設定
#         mocker.patch(
#             "youtube_uploader.youtube.Credentials.from_authorized_user_file",
#             return_value=mock_credentials,
#         )

#         # リフレッシュ失敗をモック
#         mock_credentials.refresh.side_effect = Exception("Refresh API Failed")

#         # 実行: __init__を呼び出すとAuthErrorが発生
#         with pytest.raises(AuthError) as excinfo:
#             YoutubeUploader(Path("expired_token_path"))

#         # 検証: AuthErrorメッセージに失敗内容が含まれていること
#         assert "トークンのリフレッシュに失敗しました" in str(excinfo.value)
#         mock_build.assert_not_called()

#     def test_auth_browser_flow_failed_raises_error(
#         self, mock_resolve_paths, mock_build, dummy_files, mocker
#     ):
#         """初回認証フローが失敗した場合、AuthErrorが発生することを検証"""
#         client_secrets_path, token_path = dummy_files
#         client_secrets_path.write_text('{"client_id": "dummy_id"}')
#         mock_resolve_paths.return_value = (client_secrets_path, token_path)

#         # トークンファイルが存在しない状態をシミュレーション
#         assert not token_path.exists()

#         # 認証フロー失敗をモック
#         self._mock_flow_fail(mocker)

#         # 実行: __init__を呼び出すとAuthErrorが発生
#         with pytest.raises(AuthError) as excinfo:
#             YoutubeUploader(Path("valid_path"))

#         # 検証: AuthErrorメッセージに失敗内容が含まれていること
#         assert "ブラウザ認証フローでエラーが発生しました" in str(excinfo.value)
#         mock_build.assert_not_called()


# # ----------------------------------------------------------------------
# # 3. upload_video ロジックのテスト
# # ----------------------------------------------------------------------


# def test_upload_video_file_not_found(mock_uploader_connected, mocker):
#     """動画ファイルが存在しない場合、FileNotFoundErrorを発生させることを検証"""
#     uploader, mock_youtube_service = mock_uploader_connected

#     # Path.exists() が False を返すようにモック
#     mocker.patch.object(Path, "exists", return_value=False)

#     config = YoutubeConfig(video_path=Path("non_existent.mp4"), title="Test")

#     # FileNotFoundErrorがraiseされることを期待
#     with pytest.raises(FileNotFoundError):
#         uploader.upload_video(config)

#     # APIはraiseによって呼び出されない
#     mock_youtube_service.videos().insert.assert_not_called()


# def test_upload_video_correct_body_public(mock_uploader_connected, mocker):
#     """公開設定の場合、リクエストボディが正しく構築されることを検証"""
#     uploader, mock_youtube_service = mock_uploader_connected
#     mock_insert = mock_youtube_service.videos().insert

#     mocker.patch.object(Path, "exists", return_value=True)

#     config = YoutubeConfig(
#         video_path=Path("temp.mp4"),
#         title="Test Public Video",
#         description="Public Desc",
#         tags=["a", "b", "c"],
#         category_id="1",
#         privacy_status="public",
#         selfDeclaredMadeForKids=True,
#     )

#     uploader.upload_video(config)

#     # APIが正しく呼び出されたことを検証
#     mock_insert.assert_called_once()
#     called_args, called_kwargs = mock_insert.call_args

#     # bodyの内容を検証
#     called_body = called_kwargs["body"]
#     assert called_body["snippet"]["title"] == "Test Public Video"
#     assert called_body["snippet"]["description"] == "Public Desc"
#     assert called_body["snippet"]["tags"] == ["a", "b", "c"]
#     assert called_body["snippet"]["categoryId"] == "1"
#     assert called_body["status"]["privacyStatus"] == "public"
#     assert called_body["status"]["selfDeclaredMadeForKids"] is True
#     assert "publishAt" not in called_body["status"]

#     # partも検証 (bodyのキーが全て含まれているか)
#     assert called_kwargs["part"] == "snippet,status"


# def test_upload_video_with_scheduled_publish(mock_uploader_connected, mocker):
#     """予約投稿日時が指定された場合、bodyにpublishAtがISO形式で追加されることを検証"""
#     uploader, mock_youtube_service = mock_uploader_connected
#     mock_insert = mock_youtube_service.videos().insert

#     mocker.patch.object(Path, "exists", return_value=True)

#     # タイムゾーン情報を持つ（Aware）datetimeを使用
#     schedule_time = datetime.fromisoformat("2026-01-01T10:00:00+09:00")

#     # Aware datetimeの.isoformat()は、タイムゾーン情報付きのISO形式を返します
#     schedule_time_iso = schedule_time.isoformat()

#     config = YoutubeConfig(
#         video_path=Path("temp.mp4"),
#         title="Test Schedule",
#         privacy_status="private",  # 予約投稿には private が必須
#         publish_at=schedule_time,
#     )

#     uploader.upload_video(config)

#     called_body = mock_insert.call_args.kwargs["body"]

#     # 検証: publishAtがISO形式で正しく追加されていること
#     assert called_body["status"]["privacyStatus"] == "private"
#     assert called_body["status"]["publishAt"] == schedule_time_iso


# def test_upload_video_api_insert_raises_exception(mock_uploader_connected, mocker):
#     """videos().insert() の呼び出しでAPIエラーが発生した場合、
#     UploadErrorにラップされることを検証"""
#     uploader, mock_youtube_service = mock_uploader_connected

#     # Path.exists() が True を返すようにモック
#     mocker.patch.object(Path, "exists", return_value=True)

#     # APIの挿入リクエストが例外を発生させるように設定
#     mock_youtube_service.videos().insert.side_effect = Exception("API Insert Failed")

#     config = YoutubeConfig(video_path=Path("temp.mp4"), title="Failure Test")

#     # UploadErrorがraiseされることを期待
#     with pytest.raises(UploadError) as excinfo:
#         uploader.upload_video(config)

#     assert "予期せぬエラーが発生しました: API Insert Failed" in str(excinfo.value)


# def test_upload_video_missing_id_in_response_raises_error(
#     mock_uploader_connected, mocker
# ):
#     """アップロード完了時のレスポンスにIDがない場合、UploadErrorが発生することを検証"""
#     uploader, mock_youtube_service = mock_uploader_connected
#     mock_request = mock_youtube_service.videos().insert.return_value

#     mocker.patch.object(Path, "exists", return_value=True)

#     # 最終レスポンスに 'id' を含まないように設定
#     mock_request.next_chunk.side_effect = [
#         (MagicMock(progress=lambda: 0.5), None),
#         (None, {"status": "success", "error": "none"}),  # 'id' がない
#     ]

#     config = YoutubeConfig(video_path=Path("temp.mp4"), title="Missing ID Test")

#     # UploadErrorがraiseされることを期待
#     with pytest.raises(UploadError) as excinfo:
#         uploader.upload_video(config)

#     assert "レスポンスにIDが含まれていません" in str(excinfo.value)


# def test_upload_video_completes_and_returns_response(mock_uploader_connected, mocker):
#     """アップロードが完了し、APIレスポンスが返されることを検証"""
#     uploader, mock_youtube_service = mock_uploader_connected
#     mocker.patch.object(Path, "exists", return_value=True)

#     config = YoutubeConfig(video_path=Path("temp.mp4"), title="Complete Test")

#     # リクエストモックインスタンスを取得
#     mock_request = mock_youtube_service.videos().insert.return_value

#     response = uploader.upload_video(config)

#     # 検証 1: 最終的にAPIのレスポンス辞書が返されたこと
#     assert isinstance(response, dict)
#     assert response["id"] == "VIDEO_ID_123"

#     # 検証 2: next_chunk()が複数回（チャンクアップロード）呼び出されたことを確認
#     assert mock_request.next_chunk.call_count == 2
