#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# VirtualClipboardManager モジュール

#######################################################################################
# import処理
## 標準ライブラリ
from subprocess import Popen, PIPE  # subprocessをインポート
import time
import threading
import io

## pypiライブラリ
import pyperclip
import keyboard
from PIL import Image, ImageOps
import base64

## 自作モジュール
from src.keyboard_handler import InputHandler

## その他
import clr
import win32clipboard
import win32con

#######################################################################################
# 定数


#######################################################################################
# 変数
input_handler = InputHandler()

#######################################################################################
# 関数
def load_base64_image(base64_image: str) -> Image.Image:
    """
    Base64 エンコードされた画像データを読み込み、Pillow の Image オブジェクトとして返します。

    :param base64_image: Base64 エンコードされた画像データの文字列
    :return: Pillow の Image オブジェクト
    """
    # プレフィックス 'data:image/jpeg;base64,' のような部分を取り除く
    if ',' in base64_image:
        base64_image = base64_image.split(',')[1]

    # base64 文字列をバイナリデータにデコード
    image_data = base64.b64decode(base64_image)

    # バイナリデータを io.BytesIO オブジェクトに変換
    image_stream = io.BytesIO(image_data)

    # Pillow で画像として読み込む
    image = Image.open(image_stream)
    return image

#######################################################################################
# クラス
class VirtualClipboardManager:
    """
    複数の仮想クリップボードを管理するクラス。
    
    各仮想クリップボードにはテキスト、ファイル、画像を保存することができます。
    システムクリップボードからのコンテンツコピー時に自動で内容を判別し、ラベルを設定します。
    
    主な機能:
    - 複数の仮想クリップボードを管理。
    - システムクリップボードからの自動コンテンツ判別（テキスト、ファイル、画像）。
    - コンテンツの種類に基づいて自動でラベルを設定。
    - 操作中にシステムクリップボードの内容をバックアップおよび復元。
    - テキスト、ファイルパス、画像データに対応。
    """

    def __init__(self, num_clipboards=5):
        """
        VirtualClipboardManagerの初期化を行うコンストラクタ。

        Args:
            num_clipboards (int): 管理する仮想クリップボードの数。デフォルトは5。
        
        Attributes:
            clipboards (list): 仮想クリップボードの内容を保持する辞書のリスト。
            current_clipboard_index (int): 現在のクリップボードのインデックス。デフォルトは0。
            monitoring (bool): クリップボードの監視状態を示すフラグ。
        """
        self.clipboards = [{'label': f'', 'content': '', 'type': 'text'} for i in range(num_clipboards)]
        self.current_clipboard_index = 0
        self.monitoring = False

    def get_clipboard(self, index):
        """
        仮想クリップボードから内容を取得する関数。

        Args:
            index (int): クリップボードのインデックス。

        Returns:
            内容を返します。インデックスが無効な場合はNoneを返します。
        """
        if 0 <= index < len(self.clipboards):
            return self.clipboards[index]['content']
        return None

    def get_clipboard_type(self, index):
        """
        仮想クリップボードのコンテンツタイプを取得する関数。

        Args:
            index (int): クリップボードのインデックス。

        Returns:
            str: コンテンツの種類を返します。無効なインデックスの場合はNoneを返します。
        """
        if 0 <= index < len(self.clipboards):
            return self.clipboards[index]['type']
        return None

    def set_clipboard(self, index, content, content_type='text', label=None):
        """
        仮想クリップボードに内容を設定する関数。

        Args:
            index (int): クリップボードのインデックス。
            content: 設定する内容（テキスト、ファイル、画像）。
            content_type (str): コンテンツの種類。'text'、'file'、'image'のいずれか。
            label (str or None): クリップボードのラベル。省略可能。
        """
        if 0 <= index < len(self.clipboards):
            self.clipboards[index]['content'] = content
            self.clipboards[index]['type'] = content_type
            if label:
                self.clipboards[index]['label'] = label
            else:
                self.clipboards[index]['label'] = self.generate_label(content, content_type)
            print(f'Set content to virtual clipboard {index}: {content}')

    def generate_label(self, content, content_type, image_size=128):
        """
        コンテンツに基づいてラベルを生成する関数。

        Args:
            content: 設定する内容（テキスト、ファイル、画像）。
            content_type (str): コンテンツの種類。'text'、'file'、'image'のいずれか。
            image_size (int): ラベル用画像のサイズ（ピクセル）。デフォルトは128。

        Returns:
            str: 生成されたラベルを返します。
        """
        if content_type == 'image':
            
            # png形式でエンコードしてBase64変換
            output = io.BytesIO()
            content.save(output, format='PNG', compress_level=9)
            base64_data = base64.b64encode(output.getvalue()).decode('utf-8')
            output.close()

            return f'data:image/png;base64,{base64_data}'

        elif content_type == 'text':
            return content.lstrip().replace('\n', ' ').replace('\r', '').replace(',', '，')[:120]
        elif content_type == 'file':
            return ', '.join([file.split('\\')[-1] for file in content])
        else:
            return ''
        
    def get_clipboard_label(self, index):
        """
        仮想クリップボードのラベルを取得する関数。

        Args:
            index (int): クリップボードのインデックス。

        Returns:
            str: クリップボードのラベルを返します。無効なインデックスの場合はNoneを返します。
        """
        if 0 <= index < len(self.clipboards):
            return self.clipboards[index]['label']
        return None

    def monitor_clipboard(self, index):
        """
        指定した仮想クリップボードにシステムクリップボードの変更を監視して保存する関数。

        Args:
            index (int): クリップボードのインデックス。
        """
        def monitor():
            original_content = pyperclip.paste()
            input_handler.execute_action('ctrl+c')
            time.sleep(0.1)
            previous_content = original_content

            while self.monitoring:
                current_content = pyperclip.paste()
                if current_content != previous_content:
                    self.set_clipboard(index, current_content)
                    previous_content = current_content
                    break
                time.sleep(0.1)
            
            pyperclip.copy(original_content)

        self.monitoring = True
        threading.Thread(target=monitor, daemon=True).start()

    def stop_monitoring(self):
        """
        クリップボードの監視を停止する関数。
        """
        self.monitoring = False

    def paste_clipboard(self, index):
        """
        仮想クリップボードの内容をシステムクリップボードにペーストし、元の内容を復元する関数。
        クリップボードの内容をバックアップし、処理後に復元します。

        Args:
            index (int): クリップボードのインデックス。
        """
        if 0 <= index < len(self.clipboards):
            # クリップボードの内容をバックアップ
            clipboard_backup = self.backup_clipboard()
            time.sleep(0.1)
            try:
                # 仮想クリップボードの内容をシステムクリップボードにコピー
                if self.clipboards[index]['type'] == 'text':
                    pyperclip.copy(self.clipboards[index]['content'])
                    time.sleep(0.1)
                    input_handler.execute_action('ctrl+v')
                    time.sleep(0.1)
                elif self.clipboards[index]['type'] == 'file':
                    powershell_command = 'powershell -Command "& { Set-Clipboard -LiteralPath ' + ','.join(['"{}"'.format(file) for file in self.clipboards[index]['content']]) + ' }"'
                    process = Popen(powershell_command, shell=True, stdout=PIPE, stderr=PIPE)
                    process.communicate()
                    time.sleep(0.2)
                    input_handler.execute_action('ctrl+v')
                    time.sleep(0.2)
                    print('Pasted from virtual clipboard')
                elif self.clipboards[index]['type'] == 'image':
                    self.set_system_clipboard_image(self.clipboards[index]['content'])
                    time.sleep(0.1)
                    input_handler.execute_action('ctrl+v')
                    time.sleep(0.1)

                print(f'Pasted from virtual clipboard {index}.')

            finally:
                # クリップボードの内容を復元
                self.restore_clipboard(clipboard_backup)
                print(f'Restored original clipboard after pasting from virtual clipboard {index}.')
    
    def copy_clipboard(self, index):
        """
        システムクリップボードから手動で内容を仮想クリップボードにコピーする関数。

        Args:
            index (int): クリップボードのインデックス。
        """
        if 0 <= index < len(self.clipboards):
            original_content = pyperclip.paste()
            input_handler.execute_action('ctrl+c')
            time.sleep(0.1)
            new_content = pyperclip.paste()
            self.set_clipboard(index, new_content)
            pyperclip.copy(original_content)
            print(f'Copied to virtual clipboard {index} and restored original clipboard.')

    def set_system_clipboard_file(self, file_path):
        """
        ファイルパスをシステムクリップボードに設定する関数。

        Args:
            file_path (str): 設定するファイルパス。
        """
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, file_path)
        win32clipboard.CloseClipboard()

    def get_system_clipboard_file(self):
        """
        システムクリップボードからファイルパスを取得する関数。

        Returns:
            str: ファイルパスを返します。クリップボードにファイルがない場合はNoneを返します。
        """
        win32clipboard.OpenClipboard()
        try:
            file_path = win32clipboard.GetClipboardData(win32con.CF_HDROP)
        except TypeError:
            file_path = None
        win32clipboard.CloseClipboard()
        return file_path

    def copy_file_clipboard(self, index):
        """
        システムクリップボードからファイルパスを仮想クリップボードにコピーする関数。

        Args:
            index (int): クリップボードのインデックス。
        """
        if 0 <= index < len(self.clipboards):
            file_path = self.get_system_clipboard_file()
            if file_path:
                label = ', '.join(file_path)
                self.set_clipboard(index, file_path, 'file', label)
                print(f'Copied file to virtual clipboard {index}')

    def backup_clipboard(self):
        """
        クリップボードの内容をすべての形式でバックアップする関数。
        
        Returns:
            dict: バックアップされたクリップボードのデータ。
        """
        win32clipboard.OpenClipboard()
        clipboard_data = {}
        format_id = 0

        try:
            format_id = win32clipboard.EnumClipboardFormats(0)
            while format_id:
                try:
                    data = win32clipboard.GetClipboardData(format_id)
                    clipboard_data[format_id] = data
                except TypeError:
                    pass
                format_id = win32clipboard.EnumClipboardFormats(format_id)
            
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"Error in backup_clipboard: {e}")
            time.sleep(0.1)
            win32clipboard.CloseClipboard()

        return clipboard_data
    
    def restore_clipboard(self, clipboard_data):
        """
        クリップボードの内容をバックアップから復元する関数。

        Args:
            clipboard_data (dict): バックアップされたクリップボードのデータ。
        """
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            
            for format_id, data in clipboard_data.items():
                try:
                    win32clipboard.SetClipboardData(format_id, data)
                except Exception as e:
                    print(f"Failed to restore format {format_id}: {e}")
        finally:
            win32clipboard.CloseClipboard()

    def set_system_clipboard_image(self, image):
        """
        画像データをシステムクリップボードにPNG形式とDIB(BMP)形式で設定する関数。

        Args:
            image (PIL.Image.Image): 設定する画像オブジェクト。
        """
        # 画像をPNG形式でバイナリデータに変換
        png_output = io.BytesIO()
        image.save(png_output, 'PNG')
        png_data = png_output.getvalue()
        png_output.close()

        # 画像をDIB(BMP)形式でバイナリデータに変換
        bmp_output = io.BytesIO()
        image.save(bmp_output, 'BMP')
        bmp_data = bmp_output.getvalue()[14:]  # BMPヘッダを除去
        bmp_output.close()

        # クリップボードを開いて内容をクリア
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()

        try:
            # PNG形式をクリップボードに設定
            png_format_id = win32clipboard.RegisterClipboardFormat("PNG")
            win32clipboard.SetClipboardData(png_format_id, png_data)
            
            # DIB形式をクリップボードに設定
            win32clipboard.SetClipboardData(win32con.CF_DIB, bmp_data)

        except Exception as e:
            print(f"Failed to set clipboard data: {e}")
        finally:
            win32clipboard.CloseClipboard()

    def get_system_clipboard_image(self):
        """
        システムクリップボードから画像データを取得する関数。

        Returns:
            PIL.Image.Image: 画像オブジェクトを返します。クリップボードに画像がない場合はNoneを返します。
        """
        win32clipboard.OpenClipboard()
        # クリップボードにある最初のフォーマットを取得
        format_id = win32clipboard.EnumClipboardFormats(0)
        
        # クリップボード内のすべてのフォーマットを列挙
        while format_id:
            try:
                # フォーマットIDに対応する名前を取得
                format_name = win32clipboard.GetClipboardFormatName(format_id)
                if format_name:
                    print(f"Format ID: {format_id}, Format Name: {format_name}")
                else:
                    print(f"Format ID: {format_id}, Format Name: (Standard format)")
                
                # 次のフォーマットIDを取得
                format_id = win32clipboard.EnumClipboardFormats(format_id)
            except Exception as e:
                # print(f"Error in EnumClipboardFormats: {e}")
                break

        try:
            # クリップボードのPNGフォーマットIDを使用してデータを取得
            png_format = 49532  # 先ほど列挙したIDをここに指定
            
            if win32clipboard.IsClipboardFormatAvailable(png_format):
                data = win32clipboard.GetClipboardData(png_format)
            else:
            # PNGが取得できなければCF_DIB形式を試す
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                else:
                    data = None # 画像データが見つからない場合はNoneを返す
        except TypeError:
            data = None
        win32clipboard.CloseClipboard()

        if data:
            image = Image.open(io.BytesIO(data))
            if image.mode == 'RGBA':
                # BMP形式で透過情報を保持
                return image.convert("RGBA")
            else:
                # 透過情報が無い場合
                return image.convert("RGB")
        return None

    def copy_image_clipboard(self, index):
        """
        システムクリップボードから画像データを仮想クリップボードにコピーする関数。

        Args:
            index (int): クリップボードのインデックス。
        """
        if 0 <= index < len(self.clipboards):
            image = self.get_system_clipboard_image()
            if image:
                self.set_clipboard(index, image, 'image', 'Image')
                print(f'Copied image to virtual clipboard {index}')

    def copy_clipboard_auto_from_api(self, index, new_content):
        """
        APIからのコンテンツを自動で判別し、仮想クリップボードにコピーする関数。

        Args:
            index (int): クリップボードのインデックス。
            content: コピーするコンテンツ。
            type (str): コンテンツの種類。'text'、'file'、'image'のいずれか。
        """
        if new_content["type"] == 'text':
            self.set_clipboard(index, new_content["content"], 'text', new_content["content"].lstrip().replace('\n', ' ').replace('\r', '').replace(',', '，')[:120])
            print(f'Copied text to virtual clipboard {index}')
        elif new_content["type"] == 'image':
            image = load_base64_image(new_content["content"])
            # # bmp形式に変換し、pillowで読み込む
            # output = io.BytesIO()
            # image.save(output, 'BMP')
            # data = output.getvalue()[14:]  # BMPヘッダを除去
            # output.close()
            # image = Image.open(io.BytesIO(data))
            
            self.set_clipboard(index, image, 'image')
            print(f'Copied image to virtual clipboard {index}')

    def copy_clipboard_auto(self, index):
        """
        システムクリップボードから内容を自動で判別し、仮想クリップボードにコピーする関数。
        クリップボードの内容をバックアップし、処理後に復元します。

        Args:
            index (int): クリップボードのインデックス。
        """
        if 0 <= index < len(self.clipboards):
            # クリップボードの内容をバックアップ
            clipboard_backup = self.backup_clipboard()

            input_handler.execute_action('ctrl+c')
            time.sleep(0.2)

            try:
                # ファイルの内容を確認
                file_path = self.get_system_clipboard_file()
                if file_path:
                    file_names = [file.split('\\')[-1] for file in file_path]
                    file_names = [f'"{file}"' for file in file_names]  # ファイル名を""で囲む
                    label = ', '.join(file_names)
                    self.set_clipboard(index, file_path, 'file', label)
                    print(f'Copied file to virtual clipboard {index}')
                    return

                # 画像の内容を確認
                image = self.get_system_clipboard_image()
                if image:
                    self.set_clipboard(index, image, 'image')
                    print(f'Copied image to virtual clipboard {index}')
                    return

                # テキストの内容にデフォルト設定
                new_content = pyperclip.paste()
                self.set_clipboard(index, new_content, 'text', new_content.lstrip().replace('\n', ' ').replace('\r', '').replace(',', '，')[:120])
                print(f'Copied text to virtual clipboard {index}')

            finally:
                # クリップボードの内容を復元
                self.restore_clipboard(clipboard_backup)
                print(f'Restored original clipboard after copying to virtual clipboard {index}.')
#######################################################################################
# モジュールテスト用処理
if __name__ == '__main__':
    vcb_manager = VirtualClipboardManager()

    # Example usage:
    for i in range(3):
        print(3 - i)
        time.sleep(1)
    vcb_manager.copy_clipboard_auto(0)  # 手動でシステムクリップボードを仮想クリップボード0にコピー

    print('Current content of virtual clipboard 0:', vcb_manager.get_clipboard(0))
    for i in range(3):
        print(3 - i)
        time.sleep(1)

    # クリップボード0にラベルを設定
    print('Label of virtual clipboard 0:', vcb_manager.get_clipboard_label(0))
    print(f"The type of virtual clipboard 0 is {vcb_manager.get_clipboard_type(0)}")

    # 仮想クリップボード0からシミュレーションとしてペースト
    vcb_manager.paste_clipboard(0)
