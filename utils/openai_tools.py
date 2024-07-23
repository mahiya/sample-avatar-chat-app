import os
import json
from utils.logger import logger
from utils.search import AzureSearchClient
from utils.weather import get_weather_in_tokyo
from utils.bing import BingSearchClient, BingSearchNewsCategory


class OpenAITools:

    def __init__(self, tools_definition_path: str = "openai_tools.json"):

        # ツールの定義ファイル(JSON)を読み込む
        tools_definition_path = os.path.join(os.path.dirname(__file__), tools_definition_path)
        if not os.path.exists(tools_definition_path):
            raise FileNotFoundError(f"Tools definition file not found: {tools_definition_path}")
        with open(tools_definition_path, "r") as f:
            self.tools_definition = json.load(f)

        # Bing Search Client と Azure Search Client を初期化
        self.bing_client = BingSearchClient()
        self.search_client = AzureSearchClient(index_name=os.getenv("AI_SEARCH_INDEX_NAME"))

        # Bing Search API に関する設定がされていない場合は、Web検索とニュース検索の機能を無効化
        if not os.environ.get("BING_SEARCH_API_KEY"):
            self.tools_definition = [t for t in self.tools_definition if t["function"]["name"] != "search_news"]

    def search_documents(self, query: str, count: int = 3, offset: int = 0) -> str:
        """
        Azure AI Search を使って、指定されたクエリに一致するドキュメントを検索する。

        Args:
            query (str): 検索クエリ
            count (int): 取得する検索結果の最大数
            offset (int): 検索結果のオフセット

        Returns:
            str: 検索結果のJSON文字列
        """
        logger.info(f"search_documents: query={query}, count={count}, offset={offset}")
        docs = self.search_client.search(query, top=count, skip=offset)
        return json.dumps(docs, ensure_ascii=False)

    def search_news(self, category: str = "Entertainment", count: int = 3, offset: int = 0) -> str:
        """
        Bing News Search API を使って、指定されたカテゴリに一致するニュース記事を検索する。

        Args:
            category (str): ニュースカテゴリ
            count (int): 取得する検索結果の最大数
            offset (int): 検索結果のオフセット

        Returns:
            str: 検索結果のJSON文字列
        """
        logger.info(f"search_news: category={category}, count={count}, offset={offset}")
        try:
            category = BingSearchNewsCategory(category)
        except ValueError:
            category = BingSearchNewsCategory.Entertainment
        news = self.bing_client.search_news_by_category(category, count=count, offset=offset)
        news = [{"title": n["name"], "description": n["description"]} for n in news]
        return json.dumps(news, ensure_ascii=False)

    def get_weather(self) -> str:
        """
        東京の天気情報を取得する。

        Returns:
            str: 天気情報のJSON文字列
        """
        logger.info(f"get_weather:")
        result = get_weather_in_tokyo()
        return json.dumps(result, ensure_ascii=False)
