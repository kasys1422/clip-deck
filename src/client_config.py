#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# ClientConfig モジュール

#######################################################################################
# import処理
## 標準ライブラリ
import uuid
import os
import json
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

## pypiライブラリ

## 自作モジュール

## その他
# 疑似グローバル変数管理モジュール
try:
    from global_value_handler import g
except Exception:
    pass

#######################################################################################
# 定数
CONFIG_DIR = './clients'
KEY_FILE = 'keys.json'  # クライアントごとの共通鍵を保存するファイル

#######################################################################################
# 変数


#######################################################################################
# 関数


#######################################################################################
# クラス
class ClientConfig:
    """
    クライアントごとにUUIDを生成し、設定ファイルおよび共通鍵を保存および管理するクラス。
    設定ファイルの暗号化、復号化、および送受信を行います。
    """

    def __init__(self):
        """
        クラスの初期化処理。設定ディレクトリと共通鍵ファイルが存在しない場合は作成します。
        """
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        self.keys = self._load_keys()

    def generate_uuid(self):
        """
        新しいUUIDを生成します。
        
        Returns:
            str: 生成されたUUID文字列。
        """
        return str(uuid.uuid4())

    def set_key(self, client_uuid, key):
        """
        クライアントごとの共通鍵を設定および保存します。

        Args:
            client_uuid (str): クライアントのUUID。
            key (bytes): 暗号化・復号化に使用する共通鍵。
        """
        # 共通鍵をBase64エンコードして保存
        self.keys[client_uuid] = base64.b64encode(key).decode('utf-8')
        self._save_keys()

    def get_key(self, client_uuid):
        """
        クライアントの共通鍵を取得します。

        Args:
            client_uuid (str): クライアントのUUID。

        Returns:
            bytes: クライアントの共通鍵。
        """
        key_b64 = self.keys.get(client_uuid)
        if key_b64:
            return base64.b64decode(key_b64.encode('utf-8'))
        else:
            raise ValueError(f"共通鍵が見つかりません: {client_uuid}")

    def save_config(self, client_uuid, config_data):
        """
        クライアントの設定をJSON形式でファイルに保存します。

        Args:
            client_uuid (str): クライアントのUUID。
            config_data (dict): 保存する設定データ。
        """
        config_file = os.path.join(CONFIG_DIR, f'{client_uuid}.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)

    def load_config(self, client_uuid):
        """
        クライアントの設定ファイルを読み込みます。

        Args:
            client_uuid (str): クライアントのUUID。

        Returns:
            dict: 読み込んだ設定データ。
        """
        config_file = os.path.join(CONFIG_DIR, f'{client_uuid}.json')
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"{config_file} が見つかりません")
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def encrypt_data(self, data, client_uuid):
        """
        データを暗号化します。

        Args:
            data (str): 暗号化するデータ文字列。
            client_uuid (str): クライアントのUUID。

        Returns:
            str: 暗号化されたデータをBase64エンコードした文字列。
        """
        key = self.get_key(client_uuid)
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data.encode('utf-8')) + encryptor.finalize()
        return base64.b64encode(iv + ciphertext).decode('utf-8')

    def decrypt_data(self, encrypted_data, client_uuid):
        """
        暗号化されたデータを復号化します。

        Args:
            encrypted_data (str): Base64エンコードされた暗号化データ文字列。
            client_uuid (str): クライアントのUUID。

        Returns:
            str: 復号化されたデータ文字列。
        """
        key = self.get_key(client_uuid)
        encrypted_data = base64.b64decode(encrypted_data.encode('utf-8'))
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def send_config(self, client_uuid, config_data):
        """
        クライアントの設定データを暗号化して送信する処理をシミュレートします。

        Args:
            client_uuid (str): クライアントのUUID。
            config_data (dict): 送信する設定データ。

        Returns:
            str: 暗号化された設定データ。
        """
        json_data = json.dumps(config_data)
        return self.encrypt_data(json_data, client_uuid)

    def receive_config(self, encrypted_config, client_uuid):
        """
        受信した暗号化設定データを復号化します。

        Args:
            encrypted_config (str): 暗号化された設定データ。
            client_uuid (str): クライアントのUUID。

        Returns:
            dict: 復号化された設定データ。
        """
        decrypted_data = self.decrypt_data(encrypted_config, client_uuid)
        return json.loads(decrypted_data)

    def _load_keys(self):
        """
        共通鍵を保存するファイルを読み込みます。

        Returns:
            dict: UUIDをキーとし、Base64エンコードされた共通鍵を値とする辞書。
        """
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_keys(self):
        """
        共通鍵を保存するファイルに書き込みます。
        """
        with open(KEY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.keys, f, ensure_ascii=False, indent=4)

#######################################################################################
# モジュールテスト用処理
if __name__ == '__main__':
    # テスト用のクライアント設定の例
    client_manager = ClientConfig()

    # 新しいUUIDを生成
    client_uuid = client_manager.generate_uuid()
    print(f"Generated UUID: {client_uuid}")

    # 共通鍵を生成して設定
    key = os.urandom(32)
    client_manager.set_key(client_uuid, key)

    # 設定データを作成
    config = {
        "username": "test_user",
        "password": "test_pass",
        "settings": {
            "theme": "dark",
            "notifications": True
        }
    }

    # 設定を保存
    client_manager.save_config(client_uuid, config)

    # 設定を読み込み
    loaded_config = client_manager.load_config(client_uuid)
    print(f"Loaded Config: {loaded_config}")

    # 設定を暗号化して送信シミュレーション
    encrypted_config = client_manager.send_config(client_uuid, loaded_config)
    print(f"Encrypted Config: {encrypted_config}")

    # 受信した暗号化データを復号化
    decrypted_config = client_manager.receive_config(encrypted_config, client_uuid)
    print(f"Decrypted Config: {decrypted_config}")
