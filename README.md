# Azure Speech Service - Text to Speech Avatar のサンプルアプリ

## デプロイ方法

以下の ```Deploy to Azure``` ボタンをクリックし、使用する Azure OpenAI Service アカウント情報を入力することで、必要な Azure リソースを作成し、Web アプリケーションを Azure Web Apps へデプロイしてくれます。

### Azure リソースと Web アプリケーションをデプロイする場合
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmahiya%2Fsample-avatar-chat-app%2Fmain%2Fdeploy%2Fazuredeploy.json)
  
### Azure リソースのみをデプロイする場合
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fmahiya%2Fsample-avatar-chat-app%2Fmain%2Fdeploy%2Fazuredeploy_noapp.json)

## 開発環境での実行

### 設定ファイルの用意
```.env_template```ファイルをコピーして、```.env```ファイルを生成します。  
そして、```.env```ファイルのうち、以下のパラメータを設定します。
- APPLICATIONINSIGHTS_CONNECTION_STRING
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_MODEL
- AZURE_OPENAI_TEMPERATURE
- AZURE_COSMOS_CONNECTION_STRING
- AZURE_COSMOS_DB_NAME
- AZURE_COSMOS_CONTAINER_NAME
- AZURE_SEARCH_ENDPOINT
- AZURE_SEARCH_QUERY_KEY
- AZURE_SEARCH_INDEX_NAME
- SPEECH_SERVICE_KEY
- SPEECH_SERVICE_REGION
- BING_SEARCH_API_KEY (任意)

### Python パッケージのインストール

#### (任意) Python 仮想環境の用意
必要に応じて、Python の仮想環境を構築します。以下は、venv を使った構築方法です。```.venv```という名前の仮想環境を構築しています。
```sh
python -m venv .venv
```

以下のコマンドで、仮想環境を有効化できます。
```sh
source .venv/Scripts/activate

# Power Shell の場合は以下の通り
# > . .\venv\Scripts\Activate.ps1
```

#### パッケージのインストール
以下のコマンドで、必要な Python パッケージをインストールします。
```sh
python -m pip install -r requirements.txt
```

### Web アプリケーションの実行
以下のコマンドで、Web アプリケーションを実行します。
```sh
python app.py
```

[http://127.0.0.1:5000](http://127.0.0.1:5000) へアクセスすることで、ローカルで起動している Web アプリケーションへアクセスできます。
