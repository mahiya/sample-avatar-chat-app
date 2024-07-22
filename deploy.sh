#!/bin/bash -e

# デプロイ設定
RETION='japaneast'       # Azure App Service リソースのリージョン
RESOURCE_GROUP=""        # リソースグループの名前
APP_SERVICE_PLAN_NAME="" # Azure App Service プランの名前
APP_SERVICE_NAME=""      # Azure App Service の名前

# Azure App Service での自動ビルドを有効化する
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_SERVICE_NAME \
    --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Azure App Service へ Web アプリケーションをデプロイする
az webapp up \
    --location $RETION \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN_NAME \
    --name $APP_SERVICE_NAME \
    --runtime 'PYTHON:3.11'