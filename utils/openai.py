import os
import json
from openai import AzureOpenAI
from utils.openai_tools import OpenAITools


class OpenAIClient:

    def __init__(self):
        self.client = AzureOpenAI(
            endpoint=os.environ.get("OPENAI_ENDPOINT"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            api_version=os.environ.get("OPENAI_API_VERSION", "2024-05-01-preview"),
        )

        # 各種設定値を環境変数から取得
        self.chat_model_name = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o")
        self.temperature = float(os.environ.get("OPENAI_TEMPERATURE", 0.0))
        self.max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", 4096))

        # Function Calling 用のツールを初期化
        self.tools = OpenAITools()

    def get_completion_with_tools(self, messages: list[dict]) -> any:
        """
        Azure OpenAI Service で回答を生成する (Function Calling 対応)

        Args:
            messages (list[dict]): チャットメッセージのリスト
            system_message (str): システムメッセージ
        """
        while True:

            # Azure OpenAI Service にリクエストを送信
            resp = self.client.chat.completions.create(
                model=self.chat_model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                tools=self.tools.tools_definition,
                tool_choice="auto" if len(self.tools.tools_definition) > 0 else None,
                stream=True,
            )

            # Stream 形式で返される情報から、Completion か Tool Calls かを判定して対応する
            role = ""
            tool_calls = []
            is_tool_calling = False
            for chunk in resp:

                # 1つ目は選択肢(choices)がないのでスキップ
                if not chunk.choices:
                    continue

                # choice を1つに絞る
                choice = chunk.choices[0]

                # ロールを取得
                role = choice.delta.role if choice.delta.role else role

                # ツール呼び出し(Function Calling)かどうかを判定
                if choice.delta.tool_calls:
                    is_tool_calling = True

                # ツール呼び出しがある場合は、ツール呼び出しの内容を取得
                if is_tool_calling:

                    # 最後はツール呼び出し情報はない
                    if not choice.delta.tool_calls:
                        continue

                    # ツール呼び出し情報を取得
                    for tool_call in choice.delta.tool_calls:
                        if tool_call.function.arguments:
                            tool_calls[-1]["function"]["arguments"] += tool_call.function.arguments
                        else:
                            tool_calls.append(
                                {
                                    "id": tool_call.id,
                                    "type": tool_call.type,
                                    "function": {
                                        "name": tool_call.function.name,
                                        "arguments": "",
                                    },
                                }
                            )

                # ツール呼び出しでない場合は順次ユーザに返信
                elif choice.delta.content:
                    yield choice.delta.content

            # ツール呼び出しの場合は、ツールを呼び出してその結果をメッセージに含める
            if is_tool_calling:

                messages.append(
                    {
                        "role": role,
                        "tool_calls": [
                            {
                                "id": call["id"],
                                "type": call["type"],
                                "function": {"name": call["function"]["name"], "arguments": call["function"]["arguments"]},
                            }
                            for call in tool_calls
                        ],
                    }
                )

                # 関数呼び出しを行う
                for tool_call in tool_calls:
                    func_name = tool_call["function"]["name"]
                    func_args = json.loads(tool_call["function"]["arguments"])
                    func_response = eval(f"self.tools.{func_name}(**func_args)")
                    messages.append(
                        {
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": func_name,
                            "content": func_response,
                        }
                    )

            # 一連のチャット処理が終わったら終了
            else:
                break
