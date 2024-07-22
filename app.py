import os
import json
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, Response
from utils.openai import OpenAIClient
from utils.cosmos import CosmosContainer
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Flask の初期化
app = Flask(__name__)

# .envファイルから環境変数を読み込む
load_dotenv()
SPEECH_SERVICE_KEY = os.getenv("SPEECH_SERVICE_KEY")
SPEECH_SERVICE_REGION = os.getenv("SPEECH_SERVICE_REGION")
HISTORY_MESSAGE_COUNT = int(os.getenv("HISTORY_MESSAGE_COUNT", 4))

# デバッグ実行かどうかを判定
debug = True if os.getenv("DEBUG", "false").lower() == "true" else False

# デバッグ実行でない場合のみ、Azure Application Insights によるログ出力とトレースを有効化
if not debug:
    configure_azure_monitor()
    FlaskInstrumentor().instrument_app(app)

# Azure OpenAI Service にアクセスするためのクライアントの初期化
openai_client = OpenAIClient()

# Azure Cosmos DB にアクセスするためのクライアントの初期化
cosmos_client = CosmosContainer()


@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    return app.send_static_file(path)


@app.route("/api/completion", methods=["POST"])
def get_completion_api() -> Response:
    """
    Azure OpenAI Service で回答を生成する Web API

    Returns:
        Response: 生成された回答 (ストリーム形式)
    """

    # ユーザ情報を取得
    user_id, _ = get_user_info()

    # システムメッセージを定義
    system_message = f"""
- あなたは、ユーザがあなたとの会話を楽しむために作成された女性の AI アバターです。
- ユーザが使用している言語で返信してください。
- ユーザへの質問は、外部の情報を検索し、その情報を使用して回答してください
- 生成した文章は音声合成され再生されるため、質問に対して要約した口語体の文章を出力してください(**Markdown記法や箇条書き、URLは使用しないでください**)。
- 必要に応じて、回答に以下の情報を使ってください
  - 現在時刻:  {datetime.today().strftime('%Y/%m/%d %H:%M:%S')}
    """

    # ユーザからのメッセージを取得
    message = request.json["message"]

    # ユーザの会話履歴を取得
    history = _load_messages(user_id)

    # Azure OpenAI Service - Chat Completion API で回答を生成
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    chunks = openai_client.get_completion_with_tools(messages)

    return Response(to_stream_resp(user_id, message, chunks), mimetype="text/event-stream")


def to_stream_resp(user_id: str, message: str, chunks):
    """
    チャンクをストリーム形式に変換する
    """
    content = ""
    for chunk in chunks:
        if not chunk or chunk == "[DONE]":
            continue
        content += chunk
        yield json.dumps({"content": content}).replace("\n", "\\n") + "\n"
    _save_message(user_id, {"role": "user", "content": message})
    _save_message(user_id, {"role": "assistant", "content": content})


@app.route("/api/turnServer", methods=["GET"])
def get_turn_server_info_api() -> dict:
    """
    Azure Speech Service - Text to Speech Avatar 機能を使用するための TURN サーバ情報を取得する Web API

    Returns:
        dict: TURN サーバ情報
    """
    url = f"https://{SPEECH_SERVICE_REGION}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1"
    resp = requests.get(url, headers={"Ocp-Apim-Subscription-Key": SPEECH_SERVICE_KEY}).json()
    return {"urls": [resp["Urls"][0]], "username": resp["Username"], "credential": resp["Password"]}


@app.route("/api/token", methods=["GET"])
def publish_access_token_api() -> dict:
    """
    Azure Speech Service への一時アクセストークンを発行する Web API

    Returns:
        dict: Azure Speech Service のアクセストークンとリージョン情報
    """
    url = f"https://{SPEECH_SERVICE_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": SPEECH_SERVICE_KEY, "Content-type": "application/x-www-form-urlencoded"}
    token = requests.post(url, headers=headers).text
    return {"token": token, "region": SPEECH_SERVICE_REGION}


def _load_messages(user_id: str) -> list[dict]:
    """
    会話履歴を Azure Cosmos DB から取得する

    Returns:
        list[dict]: 会話履歴
    """
    query = "SELECT * FROM c WHERE c.user_id = @user_id ORDER BY c._ts DESC OFFSET 0 LIMIT @limit"
    params = [{"name": "@user_id", "value": user_id}, {"name": "@limit", "value": HISTORY_MESSAGE_COUNT}]
    items = cosmos_client.query_items(query, params)
    items = sorted(items, key=lambda x: x["_ts"])
    return [{key: item[key] for key in {"role", "content"}} for item in items]


def _save_message(user_id: str, message: dict):
    """
    会話履歴を Azure Cosmos DB へ格納する

    Args:
        message (list[dict]): 会話履歴
    """
    message["user_id"] = user_id
    cosmos_client.upsert_item(message)


def get_user_info() -> tuple[str, str]:
    """
    ログイン中のユーザ情報を取得する

    Returns:
        tuple[str, str]: ログインユーザのIDと名前
    """
    # ヘッダーに付与されているEntra認証に関するプリンシパル情報を取得する
    # 参考: http://schemas.microsoft.com/identity/claims/objectidentifier
    principal = request.headers.get("X-Ms-Client-Principal", "")

    # プリンシパルが設定されていない場合のユーザIDとユーザ名を定義
    user_id = "00000000-0000-0000-0000-000000000000"
    user_name = ""

    # プリンシパルが設定されている場合のユーザIDとユーザ名を取得
    if principal:

        # プリンシパルをBase64デコードする
        principal = base64.b64decode(principal).decode("utf-8")
        principal = json.loads(principal)

        # プリンシパルから特定のキーの値を取得する関数を定義
        def get_princival_value(key, default):
            claims = [c["val"] for c in principal["claims"] if c["typ"] == key]
            return claims[0] if claims else default

        # ユーザーIDとユーザー名を取得する
        user_id = get_princival_value("http://schemas.microsoft.com/identity/claims/objectidentifier", "00000000-0000-0000-0000-000000000000")
        user_name = get_princival_value("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", "unknown")

    return (user_id, user_name)


if __name__ == "__main__":
    app.run(debug=debug)
