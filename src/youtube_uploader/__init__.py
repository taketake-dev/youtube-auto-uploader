"""YouTube Uploader

動画をYouTubeに簡単にアップロードするためのパッケージ

推奨インポート方法:
    from youtube_uploader import YoutubeUploader, YoutubeConfig, AuthError, UploadError
"""

from .exceptions import AuthError, UploadError, YoutubeUploaderError
from .models import YoutubeConfig
from .youtube import YoutubeUploader

__version__ = "5.0.1"

__all__ = [
    "YoutubeUploader",
    "YoutubeConfig",
    "AuthError",
    "UploadError",
    "YoutubeUploaderError",
]
