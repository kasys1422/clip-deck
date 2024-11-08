#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# keyboard handler モジュール

#######################################################################################
# import処理
# 標準ライブラリ
import ctypes
import time
import threading

# pypiライブラリ
import win32api
import win32con
import keyboard
import pyautogui

#######################################################################################
# 定数

# オーディオ関連の仮想キーコード
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_STOP = 0xB2
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1

# マイク関連のAPPCOMMAND定数
WM_APPCOMMAND = 0x319
APPCOMMAND_MIC_MUTE = 24
APPCOMMAND_MIC_VOLUME_DOWN = 25
APPCOMMAND_MIC_VOLUME_UP = 26

# マウス関連のコマンドリスト
MOUSE_COMMANDS = ["click_left", "click_right", "double_click", "move"]

#######################################################################################
# 関数


def press_key(vk_code):
    scan_code = win32api.MapVirtualKey(vk_code, 0)
    ctypes.windll.user32.keybd_event(vk_code, scan_code, 0, 0)
    time.sleep(0.05)  # 小さな遅延を追加してキー入力をエミュレート
    ctypes.windll.user32.keybd_event(
        vk_code, scan_code, win32con.KEYEVENTF_KEYUP, 0)


def send_app_command(command):
    h_mic = ctypes.windll.user32.GetForegroundWindow()
    current_state = win32api.SendMessage(
        h_mic, WM_APPCOMMAND, 0, command * 0x10000)
    return current_state != 0

#######################################################################################
# クラス


class InputHandler:
    def __init__(self):
        self.key_log = []
        self.mouse_log = []
        self.key_bindings = {}

    def on_key_event(self, event):
        """キーボードイベントを記録する"""
        self.key_log.append(event)
        print(f"Key {event.name} {event.event_type}.")

    def start_keyboard_listener(self):
        """キーボードのリスナーを開始する"""
        keyboard.hook(self.on_key_event)

    def stop_keyboard_listener(self):
        """キーボードのリスナーを停止する"""
        keyboard.unhook_all()

    def record_key_binding(self, action_name):
        """特定のアクションのためにキーボードのキーを記録する"""
        print(f"Press a key to bind it to the action '{action_name}'...")
        recorded = keyboard.record(until='esc')
        if recorded:
            self.key_bindings[action_name] = recorded
            print(f"Key binding for '{action_name}' recorded.")

    def execute_key_binding(self, action_name):
        """記録されたキーシーケンスを再生して対応するアクションを実行"""
        if action_name in self.key_bindings:
            keyboard.play(self.key_bindings[action_name])
        else:
            print(f"No key binding found for action '{action_name}'.")

    def on_click(self, x, y, button, pressed):
        """マウスクリックイベントを記録する"""
        if pressed:
            self.mouse_log.append(('click', x, y, str(button)))

    def start_mouse_listener(self):
        """マウスのリスナーを開始する"""
        def mouse_listener():
            while True:
                x, y = pyautogui.position()
                if pyautogui.mouseDown():
                    self.on_click(x, y, 'left', True)
                if pyautogui.mouseDown(button='right'):
                    self.on_click(x, y, 'right', True)
        threading.Thread(target=mouse_listener, daemon=True).start()

    def save_logs(self, file_path='logs.txt'):
        """記録されたキーボードおよびマウスのログをファイルに保存する"""
        with open(file_path, 'w') as f:
            for log in self.key_log:
                f.write(f"Keyboard {log.name} {log.event_type}\n")
            for log in self.mouse_log:
                f.write(f"Mouse {log[0]} at ({log[1]}, {log[2]}), Button: {log[3]}\n")

    def control_audio(self, action):
        """オーディオやマイクの操作を実行する"""
        if action == 'play_pause':
            press_key(VK_MEDIA_PLAY_PAUSE)
        elif action == 'stop':
            press_key(VK_MEDIA_STOP)
        elif action == 'next_track':
            press_key(VK_MEDIA_NEXT_TRACK)
        elif action == 'prev_track':
            press_key(VK_MEDIA_PREV_TRACK)
        elif action == 'volume_up':
            press_key(VK_VOLUME_UP)
        elif action == 'volume_down':
            press_key(VK_VOLUME_DOWN)
        elif action == 'mute':
            press_key(VK_VOLUME_MUTE)
        elif action == 'mic_toggle':
            send_app_command(APPCOMMAND_MIC_MUTE)
        elif action == 'mic_volume_up':
            send_app_command(APPCOMMAND_MIC_VOLUME_UP)
        elif action == 'mic_volume_down':
            send_app_command(APPCOMMAND_MIC_VOLUME_DOWN)
        else:
            raise ValueError("Invalid action for control_audio")

    def execute_mouse_command(self, action):
        """マウス関連のコマンドを実行する"""
        x, y = pyautogui.position()
        if action == "click_left":
            pyautogui.click(x, y, button='left')
        elif action == "click_right":
            pyautogui.click(x, y, button='right')
        elif action == "double_click":
            pyautogui.doubleClick(x, y)
        elif action.startswith("move"):
            _, x, y = action.split("_")
            pyautogui.moveTo(int(x), int(y))
        else:
            print(f"Unrecognized mouse action: {action}")

    def execute_action(self, command):
        """+区切りのコマンドを解析して実行する"""
        actions = command.split("+")
        remaining_keys = []

        for action in actions:
            if action in ["volume_up", "volume_down", "mute", "play_pause", "stop", "next_track", "prev_track", "mic_toggle", "mic_volume_up", "mic_volume_down"]:
                self.control_audio(action)
            elif any(action.startswith(mouse_cmd.split("_")[0]) for mouse_cmd in MOUSE_COMMANDS):
                self.execute_mouse_command(action)
            else:
                remaining_keys.append(action)

        if remaining_keys:
            keyboard_combination = "+".join(remaining_keys)
            keyboard.send(keyboard_combination)


#######################################################################################
# モジュールテスト用処理
if __name__ == '__main__':
    handler = InputHandler()

    # 文字列で指定されたアクションを実行
    # handler.execute_action("ctrl+c")  # キーボードのコントロール
    # time.sleep(1)
    # handler.execute_action("volume_up+click_right")  # 音量アップと右クリックを同時に実行
    # time.sleep(1)
    # handler.execute_action("mic_toggle+ctrl+v")  # マイクのミュートをトグルし、ctrl+vを実行
    # time.sleep(1)
    # handler.execute_action("move_100_100+double_click")  # マウスを移動してからダブルクリック
    # time.sleep(1)
