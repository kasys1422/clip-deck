# global_value_handler.py
#
# このファイルは、global_valueモジュールをインポートし、失敗した場合に代替の辞書を提供します。
# グローバル変数を管理するための統一されたインターフェースを提供します。
#
# 使用方法:
# from global_value_handler import g
#
# # グローバル変数の初期化
# g.val1 = 0
#
# def main():
#     g.val1 += 1
#     print(g.val1)
#
# if __name__ == "__main__":
#     main()
#
# この方法により、グローバル変数を簡単に管理し、プロジェクト全体で一貫したアクセス方法を提供します。
#
# 関数や他のモジュールからグローバル変数を参照または更新する際に、毎回`global`宣言を行う必要がなくなります。
# これにより、コードの可読性と保守性が向上します。
#
# クラス内からも同様にアクセスできます。
#
# 例:
# class MyClass:
#     def __init__(self):
#         from global_value_handler import g
#         self.g = g
#
#     def update_val(self):
#         self.g.val1 += 1
#
# グローバル変数の宣言と初期化は、プログラムのエントリーポイント（例: main.py）で行うことを推奨します。

class GlobalValueHandler:
    def __init__(self):
        try:
            import src.global_value as gv
            self._global_values = gv
        except ImportError as e:
            print(f"[ERROR] {e}. Using dictionary as fallback.")
            self._global_values = {}

    def __getattr__(self, name):
        if isinstance(self._global_values, dict):
            if name in self._global_values:
                return self._global_values[name]
            else:
                raise AttributeError(
                    f"'GlobalValueHandler' object has no attribute '{name}'. Tried to access '{name}' in dict.")
        else:
            if hasattr(self._global_values, name):
                return getattr(self._global_values, name)
            else:
                raise AttributeError(
                    f"'GlobalValueHandler' object has no attribute '{name}'. Tried to access '{name}' in module.")

    def __setattr__(self, name, value):
        if name == '_global_values':
            super().__setattr__(name, value)
        else:
            if isinstance(self._global_values, dict):
                self._global_values[name] = value
            else:
                setattr(self._global_values, name, value)


# インスタンスを作成して使用
g = GlobalValueHandler()
