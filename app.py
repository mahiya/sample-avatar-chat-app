import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, Response
from utils.openai import OpenAIClient
from utils.cosmos import CosmosContainer

# Flask の初期化
app = Flask(__name__)

# .envファイルから環境変数を読み込む
load_dotenv()
SPEECH_SERVICE_KEY = os.getenv("SPEECH_SERVICE_KEY")
SPEECH_SERVICE_REGION = os.getenv("SPEECH_SERVICE_REGION")
HISTORY_MESSAGE_COUNT = int(os.getenv("HISTORY_MESSAGE_COUNT", 4))

# デバッグ実行かどうかを判定
debug = True if os.getenv("DEBUG") == "true" else False

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

    system_message = f"""
- あなたは、ユーザがあなたとの会話を楽しむために作成された女性の AI アバターです。
- ユーザが使用している言語で返信してください。
- ユーザへの質問は、外部の情報を検索し、その情報を使用して回答してください
- 生成した文章は音声合成され再生されるため、質問に対して要約した口語体の文章を出力してください(**Markdown記法や箇条書き、URLは使用しないでください**)。
- 必要に応じて、回答に以下の情報を使ってください
  - 現在時刻:  {datetime.today().strftime('%Y/%m/%d %H:%M:%S')}
    """
    message = request.json["message"]
    history = _load_messages()
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    chunks = openai_client.get_completion_with_tools(messages)
    _save_message({"role": "user", "content": message})
    return Response(to_stream_resp(chunks), mimetype="text/event-stream")


def to_stream_resp(chunks):
    """
    チャンクをストリーム形式に変換する
    """
    content = ""
    for chunk in chunks:
        if not chunk or chunk == "[DONE]":
            continue
        content += chunk
        yield json.dumps({"content": content}).replace("\n", "\\n") + "\n"
    _save_message({"role": "assistant", "content": content})


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


def _load_messages() -> list[dict]:
    """
    会話履歴を Azure Cosmos DB から取得する

    Returns:
        list[dict]: 会話履歴
    """
    query = "SELECT * FROM c ORDER BY c._ts DESC OFFSET 0 LIMIT @limit"
    params = [{"name": "@limit", "value": HISTORY_MESSAGE_COUNT}]
    items = cosmos_client.query_items(query, params)
    items = sorted(items, key=lambda x: x["_ts"])
    return [{key: item[key] for key in {"role", "content"}} for item in items]


def _save_message(message: dict):
    """
    会話履歴を Azure Cosmos DB へ格納する

    Args:
        message (list[dict]): 会話履歴
    """
    cosmos_client.upsert_item(message)


if __name__ == "__main__":
    app.run(debug=debug)
