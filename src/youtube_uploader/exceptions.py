class YoutubeUploaderError(Exception):
    """YouTube Uploader パッケージのエラーの基底クラス"""

    pass


class AuthError(YoutubeUploaderError):
    """認証またはトークンの処理中に問題が発生した場合の例外"""

    pass


class UploadError(YoutubeUploaderError):
    """動画のアップロードリクエスト中に問題が発生した場合の例外"""

    pass
