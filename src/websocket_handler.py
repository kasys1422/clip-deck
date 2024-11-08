#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# WebSocketServer モジュール

#######################################################################################
# import処理
# 標準ライブラリ
import asyncio
import sys
# import nest_asyncio
# nest_asyncio.apply()
import base64
import json
import os
from pathlib import Path
import threading
import uuid

# pypiライブラリ
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

# 自作モジュール

# その他
# 疑似グローバル変数管理モジュール
try:
    from global_value_handler import g
except Exception:
    pass

#######################################################################################
# 定数
SEND_INTERVAL = 2  # ループの実行間隔（秒）

#######################################################################################
# クラス

class WebSocketConnectionManager:
    """
    WebSocket接続を管理し、クライアントごとの通信を処理するクラス。
    クライアントごとの定期タスクを管理します。
    """

    def __init__(self):
        """
        クラスの初期化処理。接続中のWebSocketを管理するためのリストを初期化します。
        """
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        クライアントからの接続を受け入れ、アクティブな接続としてリストに追加します。

        Args:
            websocket (WebSocket): クライアントからのWebSocket接続。
        """
        self.is_first = True
        await websocket.accept()
        self.active_connections.append(websocket)
        asyncio.create_task(self.periodic_task(websocket))

    def disconnect(self, websocket: WebSocket):
        """
        クライアントからの接続を切断し、アクティブな接続リストから削除します。

        Args:
            websocket (WebSocket): 切断されたWebSocket接続。
        """
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message, websocket: WebSocket):
        """
        特定のクライアントにメッセージを送信します。

        Args:
            message (str): 送信するメッセージ。
            websocket (WebSocket): メッセージを送信するWebSocket接続。
        """
        if key_manager is not None:
            message = key_manager.encrypt(message.encode())
        if type(message) == dict:
            message = json.dumps(message)
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """
        接続中の全てのクライアントにメッセージをブロードキャストします。

        Args:
            message (str): 送信するメッセージ。
        """
        if key_manager is not None:
            message = key_manager.encrypt(message.encode())
        for connection in self.active_connections:
            await connection.send_text(message)

    async def periodic_task(self, websocket: WebSocket):
        """
        クライアントごとに一定時間おきに実行するループ。

        Args:
            websocket (WebSocket): WebSocketプロトコルオブジェクト。
        """
        self.is_first = True
        buffer = {}
        try:
            while True:
                # ここで定期的に実行したい処理を行う
                message = json.dumps(
                    {"status": "alive", "message": "Periodic update"})
                await self.send_personal_message(message, websocket)
                # print(f"Sent periodic message to {
                #       websocket.client}: {message}")
                global periodic_task
                if periodic_task is not None:
                    async def send_message(message):
                        await self.send_personal_message(message, websocket)
                    await periodic_task(send_message, self.is_first, buffer)
                    self.is_first = False
                await asyncio.sleep(SEND_INTERVAL)
        except asyncio.CancelledError:
            print(f"Periodic task cancelled for client: {websocket.client}")
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            print(f"Error in periodic task: {e}")

#######################################################################################
# 変数
app = FastAPI()
key_manager = None
# key_manager = KeyManager(Path("./shared_key.bin"))
manager = WebSocketConnectionManager()
callback = None
periodic_task = None

#######################################################################################
# FastAPIルーティング
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket接続のエンドポイント。
    クライアントからの接続を処理し、メッセージの受信および送信を行います。

    Args:
        websocket (WebSocket): クライアントからのWebSocket接続。
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if key_manager is not None:
                data = key_manager.decrypt(data)
            print(f"Received message: {data}")
            response = process_message(data)
            await manager.send_personal_message(response, websocket)
            print(f"Sent message to {websocket.client}: {response}")
            async def send_message(message):
                await manager.send_personal_message(message, websocket)
            await asyncio.sleep(0.1)
            await periodic_task(send_message, True)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client {websocket.client} disconnected")

# /publicフォルダをルートパス(/)にホスト
app.mount("/", StaticFiles(directory="public", html=True), name="public")

#######################################################################################
# 関数
def process_message(message: str) -> str:
    """
    クライアントから受信したメッセージを処理します。
    必要に応じて、ここでメッセージの処理ロジックを実装します。

    Args:
        message (str): 受信したメッセージ。

    Returns:
        str: 処理された結果を返します（ここではエコーバック）。
    """
    # メッセージをJSON形式にパース（必要に応じて）
    try:
        message_data = json.loads(message)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON format"})

    try:
        global callback
        if callback:
            callback_response_data = callback(message_data, manager)
            return json.dumps(callback_response_data)
        else:
            return json.dumps({"error": "No callback function set"})
    except Exception as e:
        print(f"Error in callback: {e}")
        return json.dumps({"error": f"Error in callback: {e}"})


async def start_async_server(callback_func = None, periodic_task_func = None):
    """
    Uvicornを使用してFastAPIアプリケーションを非同期で開始するメソッド。
    """
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info", ws_max_size=104857600)
    server = uvicorn.Server(config)
    global callback
    callback = callback_func
    global periodic_task
    periodic_task = periodic_task_func
    await asyncio.create_task(server.serve())

def start_server(callback_func=None, periodic_task_func=None, blocking=False):
    """
    Uvicornを使用してFastAPIアプリケーションをスレッドで開始するメソッド。
    """
    # Freeze環境下での特殊処理
    if getattr(sys, 'frozen', False):
        sys.stdout = open(os.devnull, 'w')
    config = uvicorn.Config(app, host="0.0.0.0", port=22282, log_level="info", ws_max_size=104857600)
    server = uvicorn.Server(config)
    
    global callback
    callback = callback_func
    global periodic_task
    periodic_task = periodic_task_func
    
    # サーバーを別スレッドで開始
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    
    # 必要に応じて定期タスクも別スレッドで実行
    # if periodic_task_func:
    #     periodic_task_thread = threading.Thread(target=periodic_task_func, daemon=True, args=(manager,))
    #     periodic_task_thread.start()

    # メインスレッドが終了しないように待機
    if blocking:
        server_thread.join()
        

#######################################################################################
# モジュールテスト用処理
if __name__ == '__main__':
    pass
