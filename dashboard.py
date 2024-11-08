#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# Clip Deck App
VERSION = "0.0.1"

#######################################################################################
# import処理
# 標準ライブラリ
import asyncio
import json
import os
import socket
import webbrowser

# pypiライブラリ
import tkinter as tk
from tkinter import messagebox
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw, ImageTk
import qrcode
from pystray import Icon, MenuItem, Menu
# import nest_asyncio
# nest_asyncio.apply()
from fastapi import WebSocket

# 自作モジュール
from src.clipboard_manager import input_handler
from src.clipboard_manager import VirtualClipboardManager
from src.keyboard_handler import InputHandler
from src.hardware_info import SystemMonitor
from src.audio_info import MediaInfoManager
from src.websocket_handler import start_async_server, start_server, WebSocketConnectionManager, key_manager

# その他
# 空ファイルを用いた疑似グローバル変数を定義
from global_value_handler import g
g.VERSION = VERSION

#######################################################################################
# 定数
NUM_CLIPBOARDS = 10

#######################################################################################
# グローバル変数
audio_info_manager = MediaInfoManager()
system_monitor = SystemMonitor()
clipboard_manager = VirtualClipboardManager(num_clipboards=NUM_CLIPBOARDS)

#######################################################################################
# 関数
def get_local_ip():
    """
    ローカルIPアドレスを取得する関数。

    Returns:
        str: ローカルIPアドレス。
    """
    try:
        # ダミーの接続を使ってローカルIPを取得
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 8.8.8.8 (GoogleのDNSサーバー) への接続を模倣
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception as e:
        print(f"Error obtaining local IP: {e}")
        local_ip = "127.0.0.1"  # フォールバックとしてlocalhostを返す

    return local_ip

def get_clipboard_info():
    """
    クリップボード情報を取得する関数。
    """
    info = {"type": "clipboard_info"}
    for i in range(NUM_CLIPBOARDS):
        label = clipboard_manager.get_clipboard_label(i)
        # print(f"CLIPBOARD {i}: {label}")
        clp_type = clipboard_manager.get_clipboard_type(i)
        # print(f"CLIPBOARD {i} type: {clp_type}")
        if clp_type == "text":
            data = clipboard_manager.get_clipboard(i)
            info[f"clipboard_{i}"] = {
                "label": label,
                "type": clp_type,
                "data": data
            }
        else:
            info[f"clipboard_{i}"] = {
                "label": label,
                "type": clp_type
            }
    return info

def process_message(message: str, ws: WebSocketConnectionManager) -> str:
    """
    クライアントから受信したメッセージを処理します。
    必要に応じて、ここでメッセージの処理ロジックを実装します。

    Args:
        message (str): 受信したメッセージ。

    Returns:
        str: 処理された結果を返します（ここではエコーバック）。
    """
    # メッセージをJSON形式にパース
    # print(f"Received message: {message}")

    if message["type"] == "input":
        # 許可されたキーボード入力を処理
        if message["command"] == "play_pause" or message["command"] == "next_track" or message["command"] == "prev_track":
            input_handler.execute_action(message["command"])
            return {"response": f"Input command ({message['command']}) executed.", "status": "success"}
        else:
            return {"response": f"Input command ({message['command']}) not allowed.", "status": "error"}
    elif message["type"] == "clipboard_copy":
        # クリップボード操作を処理
        clipboard_manager.copy_clipboard_auto(message["id"])
        clipboard_info = get_clipboard_info()
        return {
            "type": "clipboard_info",
            "data": clipboard_info
        }
    elif message["type"] == "clipboard_paste":
        clipboard_manager.paste_clipboard(message["id"])
        clipboard_info = get_clipboard_info()
        return {
            "type": "clipboard_info",
            "data": clipboard_info
        }
    elif message["type"] == "clipboard_upload":
        clipboard_manager.copy_clipboard_auto_from_api(message["id"], message["data"])
        clipboard_info = get_clipboard_info()
        return {
            "type": "clipboard_info",
            "data": clipboard_info
        }
    elif message["type"] == "clipboard_download":
        data = clipboard_manager.get_clipboard(message["id"])
        clipboard_info = get_clipboard_info()
        return {
            "type": "clipboard_download",
            "data": data
        }
    else:
        response_data = {
            "response": message,
            "status": "success"
        }

        return response_data


async def periodic_task_function(websocket_send_function, is_first=False, buffer=None):
    """
    定期的に実行するタスクを定義する関数。
    ここでは、定期的にシステム情報を取得してクライアントに送信します。

    Args:
        websocket (WebSocket): WebSocket接続オブジェクト。
    """
    # システム情報を取得
    cpu_usage = system_monitor.get_cpu_usage()
    memory_usage = system_monitor.get_memory_usage()
    disk_usage = system_monitor.get_disk_usage()
    network_usage = system_monitor.get_network_usage()
    cpu_name = system_monitor.get_cpu_name()
    cpu_cores = system_monitor.get_cpu_core_count()
    cpu_threads = system_monitor.get_cpu_thread_count()
    # print(f"CPU Name: {cpu_name}")
    memory_info = system_monitor.get_total_memory_info()
    # print(f"Memory Info: {memory_info}")
    # システム情報を送信
    response_data = {
        "type": "system_info",
        "data": {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "network_usage": network_usage
        },
        "info": {
            "cpu_name": cpu_name,
            "cpu_cores": cpu_cores,
            "cpu_threads": cpu_threads,
            "memory_info": memory_info
        }
    }
    await websocket_send_function(response_data)

    # オーディオ情報を取得
    media_info, info_changed = await audio_info_manager.get_media_info_async(quality=60)
    if info_changed or is_first or True:
        # オーディオ情報が変更された場合のみ送信
        response_data = {
            "type": "audio_info",
            "data": media_info
        }
        if buffer is None:
            await websocket_send_function(response_data)
        else:
            if "audio_info" in buffer:
                if buffer["audio_info"] != response_data:
                    await websocket_send_function(response_data)
        if buffer is not None:
            buffer["audio_info"] = response_data

    # クリップボード情報を送信
    clipboard_info = get_clipboard_info()
    response_data = {
        "type": "clipboard_info",
        "data": {}
    }

    # bufferが存在しない場合、全てのクリップボード情報を送信する
    if buffer is None:
        for i in range(NUM_CLIPBOARDS):
            clipboard_key = f"clipboard_{i}"
            response_data["data"][clipboard_key] = clipboard_info.get(clipboard_key, {})
        await websocket_send_function(response_data)
    else:
        # 変更されたクリップボードのみをresponse_dataに追加する
        for i in range(NUM_CLIPBOARDS):
            clipboard_key = f"clipboard_{i}"
            new_clipboard_data = clipboard_info.get(clipboard_key, {})
            old_clipboard_data = buffer.get("clipboard_info", {}).get(clipboard_key, {})
            
            if new_clipboard_data != old_clipboard_data:
                response_data["data"][clipboard_key] = new_clipboard_data
        
        # もしresponse_dataに変更があった場合のみ送信する
        if response_data["data"]:
            await websocket_send_function(response_data)

    # bufferを更新する
    if buffer is not None:
        buffer["clipboard_info"] = clipboard_info

def create_image(width, height, color1, color2):
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image

def show_qr_window():
    root = tk.Tk()
    root.title("Mobile Deck")
    ip = get_local_ip()
    qr_data = f"http://{ip}:{22282}/dashboard.html"
    # qr_data = f"http://{ip}:{22282}/dashboard.html#{str(key_manager.key_b64.decode('utf-8'))}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    img_label = tk.Label(root)
    img_label.img = ImageTk.PhotoImage(img)
    img_label['image'] = img_label.img
    img_label.pack(pady=10)
    
    link_label = tk.Label(root, text=qr_data, fg="blue", cursor="hand2")
    link_label.pack(pady=10)
    link_label.bind("<Button-1>", lambda e: webbrowser.open_new(qr_data))
    
    root.mainloop()

def on_quit(icon, item):
    icon.stop()
    exit(0)

def on_show_qr(icon, item):
    show_qr_window()

# 外部ファイルからアイコンを読み込み
icon_path = "icon.png"  # もしくは "icon.ico"
if not os.path.exists(icon_path):
    raise FileNotFoundError(f"{icon_path} が見つかりません")

icon_image = Image.open(icon_path)

icon = Icon(
    "mobile_deck",
    icon_image,
    title="Mobile Deck",
    menu=Menu(
        MenuItem("Show QR Code", on_show_qr),
        MenuItem("Quit", on_quit)
    )
)

#######################################################################################
# メイン処理
def main():
    """
    メイン処理を行う関数。
    """
    # 初期化処理
    start_server(process_message, periodic_task_function)
    print("Server started.")
    icon.run()
    pass


if __name__ == '__main__':
    main()
    pass
