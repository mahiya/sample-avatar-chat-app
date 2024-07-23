import os
import uuid
from typing import List, Dict
from azure.identity import DefaultAzureCredential
from azure.core.credentials import TokenCredential
from azure.cosmos import PartitionKey
from azure.cosmos.cosmos_client import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError


class CosmosContainer:

    def __init__(
        self,
        account_name: str = None,
        db_name: str = None,
        container_name: str = None,
        connection_string: str = None,
        credential: TokenCredential = DefaultAzureCredential(),
    ):
        account_name = account_name or os.getenv("COSMOS_ACCOUNT_NAME")
        db_name = db_name or os.getenv("COSMOS_DB_NAME")
        container_name = container_name or os.getenv("COSMOS_CONTAINER_NAME")
        connection_string = connection_string or os.getenv("COSMOS_CONNECTION_STRING")

        # Azure Cosmos DB アカウントを参照する
        if connection_string:
            client = CosmosClient.from_connection_string(connection_string)
        else:
            client = CosmosClient(
                url=f"https://{account_name}.documents.azure.com:443/",
                credential=credential,
            )

        # データベースを参照する (存在しない場合は作成する)
        client.create_database_if_not_exists(id=db_name)
        database = client.get_database_client(db_name)

        # コンテナを参照する (存在しない場合は作成する)
        database.create_container_if_not_exists(id=container_name, partition_key=PartitionKey(path=f"/id"))
        self.container = database.get_container_client(container_name)

    def query_items(self, query: str, parameters: List[Dict] = None, enable_cross_partition_query: bool = True) -> List[Dict]:
        """
        Azure Cosmos DB にクエリを実行する

        Args:
            query (str): クエリ文字列
            parameters (list[dict]): クエリパラメータ
            enable_cross_partition_query (bool): クロスパーティションクエリを許可するか

        Returns:
            list[dict]: クエリ結果
        """
        items = self.container.query_items(query, parameters=parameters, enable_cross_partition_query=enable_cross_partition_query)
        return [i for i in items]

    def get_item(self, id: str) -> Dict:
        """
        Azure Cosmos DB から指定されたIDのアイテムを取得する

        Args:
            id (str): アイテムID
        """
        try:
            return self.container.read_item(item=id, partition_key=id)
        except CosmosResourceNotFoundError:
            return None

    def upsert_item(self, item: dict):
        """
        Azure Cosmos DB にアイテムを追加または更新する

        Args:
            item (dict): 追加または更新するアイテム
        """
        try:
            if "id" not in item:
                item["id"] = str(uuid.uuid4())
            return self.container.upsert_item(item)
        except CosmosResourceNotFoundError:
            return None

    def delete_item(self, id: str):
        """
        Azure Cosmos DB から指定されたIDのアイテムを削除する

        Args:
            id (str): アイテムID
        """
        try:
            self.container.delete_item(item=id, partition_key=id)
        except CosmosResourceNotFoundError:
            pass
