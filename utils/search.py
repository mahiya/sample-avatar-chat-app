import os
import json
import requests
from tqdm import tqdm
from concurrent.futures.thread import ThreadPoolExecutor
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizableTextQuery, VectorizedQuery


class AzureSearchClient:

    def __init__(
        self,
        endpoint: str = None,
        index_name: str = None,
        credential: TokenCredential = None,
        key: str = None,
        api_version: str = None,
    ):
        self.endpoint = endpoint or os.getenv("AI_SEARCH_ENDPOINT")
        self.index_name = index_name or os.getenv("AI_SEARCH_INDEX_NAME")
        self.api_version = api_version or os.getenv("AI_SEARCH_API_VERSION", "2024-05-01-preview")
        self.key = key or os.getenv("AI_SEARCH_API_KEY")
        self.use_semantic_search = True if os.getenv("AI_SEARCH_USE_SEMANTIC_SEARCH", "false") == "true" else False
        self.vector_field_names = os.getenv("AI_SEARCH_VECTOR_FIELD_NAMES", "")
        self.vector_field_names = self.vector_field_names.split(",") if self.vector_field_names else []

        if credential:
            credential = DefaultAzureCredential()
        elif self.key:
            credential = AzureKeyCredential(self.key)

        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=credential,
            api_version=self.api_version,
        )
        self.search_client = self.index_client.get_search_client(self.index_name)

    def create_index(self, json_file_path: str, vectorizer: dict = None) -> int:
        """
        インデックスを作成する

        Args:
            json_file_path (str): インデックス定義のJSONファイルパス
            vectorizer (dict): ベクトル化の設定

        Returns:
            int: HTTP ステータスコード
        """

        # インデックス定義を読み込む
        with open(json_file_path, "r") as f:
            data = json.load(f)

        # インデックス名を設定
        data["name"] = self.index_name

        # ベクトル検索の設定を追加
        if "vectorSearch" in data and vectorizer:
            data["vectorSearch"]["vectorizers"][0]["azureOpenAIParameters"] = vectorizer

        # インデックスを作成
        resp = requests.post(
            f"{self.endpoint}/indexes?api-version={self.api_version}",
            data=json.dumps(data),
            headers={"Content-Type": "application/json", "api-key": self.key},
        )

        # エラーチェック
        if resp.status_code != 201:
            print(resp.content)
        resp.raise_for_status()

        # HTTP ステータスコードを返す
        return resp.status_code

    def delete_index(self):
        """
        インデックスを削除する
        """
        self.index_client.delete_index(self.index_name)

    def check_index_exists(self) -> bool:
        """
        インデックスが存在するか確認する

        Returns:
            bool: インデックスが存在する場合は True
        """
        try:
            self.index_client.get_index(self.index_name)
            return True
        except ResourceNotFoundError:
            return False

    def recreate_index(self, json_file_path: str, vectorizer: dict = None) -> int:
        """
        インデックスを再作成する

        Args:
            json_file_path (str): インデックス定義のJSONファイルパス
            vectorizer (dict): ベクトル化の設定

        Returns:
            int: HTTP ステータスコード
        """
        if self.check_index_exists():
            self.delete_index()
        return self.create_index(json_file_path, vectorizer=vectorizer)

    def index_documents(self, docs: list[dict], chunk_size: int = 250):
        """
        インデックスにドキュメントを追加する

        Args:
            docs (list[dict]): ドキュメントのリスト
            chunk_size (int): １つのスレッドで一度にアップロードするドキュメント数
        """
        chunks = [docs[i : i + chunk_size] for i in range(0, len(docs), chunk_size)]
        upload_documents = lambda d: self.search_client.upload_documents(documents=d)
        with ThreadPoolExecutor(max_workers=4) as executor:
            threads = [executor.submit(upload_documents, c) for c in chunks]
            [t.result() for t in tqdm(threads)]

    def delete_documents(self, ids: list[str]):
        """
        インデックスのドキュメントを削除する

        Args:
            ids (list[str]): 削除するドキュメントのIDリスト
        """
        docs = [{"id": id} for id in ids]
        self.search_client.delete_documents(documents=docs)

    def get_document(self, key: str):
        """
        指定したキーのインデックスのドキュメントを取得する

        Args:
            key (str): ドキュメントのキー

        Returns:
            dict: ドキュメント (存在しない場合は None を返す)
        """
        try:
            return self.search_client.get_document(key=key)
        except ResourceNotFoundError:
            return None

    def get_index_statistics(self) -> dict:
        """
        インデックスの統計情報を取得する
        """
        return self.index_client.get_index_statistics(self.index_name)

    def search(self, query: str = None, query_vector: list[float] = None, top: int = 10, skip: int = 0, filter: str = None) -> list[dict]:
        """
        Azure AI Search によるドキュメント検索を実行する

        Args:
            query (str): 検索クエリ
            query_vector (list[float]): 検索ベクトル
            top (int): 取得する検索結果の最大数
            skip (int): 検索結果のオフセット
            filter (str): フィルタ条件

        Returns:
            list[dict]: 検索結果のドキュメント一覧
        """
        docs = self.search_client.search(
            search_text=query,
            query_type="semantic" if self.use_semantic_search else "full",
            filter=filter,
            top=top,
            skip=skip,
            vector_queries=(
                [
                    (
                        VectorizableTextQuery(
                            k_nearest_neighbors=top,
                            fields=field_name,
                            text=query,
                        )
                        if query_vector is None
                        else VectorizedQuery(
                            k_nearest_neighbors=top,
                            fields=field_name,
                            vector=query_vector,
                        )
                    )
                    for field_name in self.vector_field_names
                ]
            ),
        )
        return [d for d in docs]  # Paged item -> list
