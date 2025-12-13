"""YouTube Uploader

動画をYouTubeに簡単にアップロードするためのパッケージ
"""

from .exceptions import AuthError, UploadError
from .models import YoutubeConfig
from .youtube import YoutubeUploader

__version__ = "5.0.0"

__all__ = [
    "YoutubeUploader",
    "YoutubeConfig",
    "AuthError",
    "UploadError",
]
