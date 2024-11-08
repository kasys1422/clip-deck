# global_value.py
#
# このファイルは、プロジェクト全体で使用されるグローバル変数を管理するためのモジュールです。
# 各モジュールでこのファイルをインポートし、`g`というエイリアスを使用してグローバル変数にアクセスします。
#
# 使用例:
# from global_value_handler import g
#
# g.val1 = 100
#
# 関数や他のモジュールからグローバル変数を参照または更新する際に、毎回`global`宣言を行う必要がなくなります。
# これにより、コードの可読性と保守性が向上します。
#
# グローバル変数の宣言と初期化は、プログラムのエントリーポイント（例: main.py）で行うことを推奨します。
#
# 例:
# main.py
# from global_value_handler import g
# g.val1 = 0
#
# my_function.py
# from global_value_handler import g
# def update_val1():
#     g.val1 += 1
#
# このようにして、プロジェクト全体で一貫してグローバル変数を使用できます。

# このファイルに実際の変数宣言や値を記述する必要はありません。
# 空のままにしておいてください。
