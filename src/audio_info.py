#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# MediaInfoManager モジュール

#######################################################################################
# import処理
## 標準ライブラリ
import asyncio
# import nest_asyncio
# nest_asyncio.apply()
import base64
import io

## pypiライブラリ
from PIL import Image, ImageOps

## 自作モジュール

## その他
try:
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
    from winsdk.windows.storage.streams import DataReader, Buffer, InputStreamOptions
except Exception:
    pass

#######################################################################################
# 定数


#######################################################################################
# 変数


#######################################################################################
# 関数


#######################################################################################
# クラス
class MediaInfoManager:
    """
    音楽再生情報を管理するクラス。
    
    現在再生中のメディア情報（アーティスト名、曲名、アルバム情報、サムネイル画像など）を取得し、
    以前の情報と比較して変化があったかをチェックする機能を提供します。
    """
    def __init__(self):
        """
        MediaInfoManagerの初期化を行うコンストラクタ。
        
        Attributes:
            previous_info (dict or None): 前回取得したメディア情報を保存する辞書。初期値はNone。
        """
        self.previous_info = None
        self.change_count = 0

    async def read_stream_into_buffer(self, stream_ref, buffer):
        """
        ストリームをバッファに読み込む非同期関数。
        
        Args:
            stream_ref: 読み込み元のストリーム参照。
            buffer (Buffer): データを格納するためのバッファオブジェクト。
        
        Returns:
            None
        """
        try:
            readable_stream = await stream_ref.open_read_async()
            await readable_stream.read_async(buffer, buffer.capacity, InputStreamOptions.READ_AHEAD)
        except Exception as e:
            print(f"Error reading stream: {e}")

    async def get_media_info_async(self, image_size=150, lossless=False, quality=90):
        """
        現在のメディア情報を非同期で取得する関数。
        
        Args:
            image_size (int): サムネイル画像のサイズ。デフォルトは150ピクセル。
        
        Returns:
            tuple: 現在のメディア情報を格納した辞書と、情報が更新されたかどうかのブール値のタプル。
        """
        sessions = await MediaManager.request_async()
        current_session = sessions.get_current_session()
        
        if current_session:
            info = await current_session.try_get_media_properties_async()
            artist = info.artist
            title = info.title
            album_title = info.album_title
            album_artist = info.album_artist
            track_number = info.track_number
            thumbnail_stream_ref = info.thumbnail

            if self.previous_info is None:
                self.change_count = 0
            elif self.previous_info["title"] != title:
                self.change_count = 0
            elif self.change_count < 10:
                self.change_count += 1
            else:
                pass

            
            album_thumbnail = None
            if thumbnail_stream_ref:
                async def create_thumbnail(image, image_size):
                    thumb_read_buffer = Buffer(5000000)
                    
                    # `asyncio.run_in_executor` を使用して非同期タスクを実行
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, self._blocking_read_stream, thumbnail_stream_ref, thumb_read_buffer)
                    
                    buffer_reader = DataReader.from_buffer(thumb_read_buffer)
                    byte_buffer = bytearray(thumb_read_buffer.length)
                    buffer_reader.read_bytes(byte_buffer)
                    image = Image.open(io.BytesIO(byte_buffer))
                    image = ImageOps.contain(image, (image_size, image_size), method=Image.LANCZOS)
                    background = Image.new('RGB', (image_size, image_size), (255, 255, 255))
                    offset = ((image_size - image.width) // 2, (image_size - image.height) // 2)
                    background.paste(image, offset)

                    with io.BytesIO() as output:
                        if lossless == True:
                            background.save(output, format="WEBP", quality=100, lossless=True)
                        else:
                            background.save(output, format="WEBP", quality=quality)
                        album_thumbnail = output.getvalue()
                        album_thumbnail = base64.b64encode(album_thumbnail).decode()
                        return album_thumbnail
                if self.previous_info is None or self.previous_info["title"] != title:
                    album_thumbnail = await create_thumbnail(album_thumbnail, image_size)
                elif self.change_count == 3:
                    album_thumbnail = await create_thumbnail(album_thumbnail, image_size)
                # サムネイルが無いはずなのにサムネイルを取得できた場合は再取得
                elif self.previous_info["album_thumbnail"] is None:
                    album_thumbnail = await create_thumbnail(album_thumbnail, image_size)
                # 曲が変わっていない場合はサムネイルを再利用
                else:
                    album_thumbnail = self.previous_info["album_thumbnail"]
            current_info = {
                "artist": artist,
                "title": title,
                "album_title": album_title,
                "album_artist": album_artist,
                "track_number": track_number,
                "album_thumbnail": album_thumbnail,
            }
            
            if self.previous_info is None or self.has_info_changed(current_info):
                self.previous_info = current_info
                return current_info, True
            else:
                self.previous_info = current_info
                return current_info, False
        else:
            return None, False

    def _blocking_read_stream(self, stream_ref, buffer):
        """
        ストリームをバッファに同期的に読み込むブロッキング関数。
        非同期タスクとして別スレッドで実行されることを前提とする。
        """
        try:
            # open_read_async() を同期的に処理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.read_stream_into_buffer(stream_ref, buffer))
        except Exception as e:
            print(f"Error in blocking read stream: {e}")

    def has_info_changed(self, current_info):
        """
        現在のメディア情報と前回のメディア情報を比較し、変化があったかどうかを確認する関数。
        
        Args:
            current_info (dict): 現在のメディア情報を格納した辞書。
        
        Returns:
            bool: メディア情報に変化があった場合はTrue、無かった場合はFalseを返す。
        """
        if self.previous_info is None:
            return True
        return any(
            self.previous_info[key] != current_info[key]
            for key in ["artist", "title", "album_title", "album_artist", "track_number"]
        )

    def get_media_info(self):
        """
        現在のメディア情報を同期的に取得する関数。
        
        Returns:
            dict or None: 現在のメディア情報を格納した辞書。取得に失敗した場合はNone。
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.get_media_info_async())
    
    def get_current_media_info(self):
        """
        以前に取得したメディア情報を返す関数。
        
        Returns:
            dict or None: 以前に取得したメディア情報を格納した辞書。情報が無い場合はNone。
        """
        return self.previous_info


#######################################################################################
# モジュールテスト用処理
if __name__ == '__main__':
    pass
