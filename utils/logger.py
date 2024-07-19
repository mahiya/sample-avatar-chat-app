import os
import logging

# ロギングの設定
logger = logging.getLogger(__name__)

# デバッグ実行かどうかを判定
debug = True if os.getenv("DEBUG") == "true" else False

# デバックモードの場合は、コンソールにもログを出力する
if debug:

    # コンソールハンドラの作成
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # フォーマッタの作成
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # ハンドラをロガーに追加
    logger.addHandler(console_handler)

# ログ出力レベルを設定
logger.setLevel(logging.DEBUG if debug else logging.INFO)
