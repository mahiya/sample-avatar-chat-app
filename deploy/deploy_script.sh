#!/bin/bash -e

# Download search index definition JSON file
curl -o search_index.json https://raw.githubusercontent.com/mahiya/sample-avatar-chat-app/main/deploy/search_index.json

# Create search index in Azure AI Search
curl -X PUT https://$searchServiceName.search.windows.net/indexes/$searchServiceIndexName?api-version=2024-05-01-preview \
    -H 'Content-Type: application/json' \
    -H 'api-key: '$searchServiceApiKey \
    -d "$(sed -e "s|{{VECTORIZER_RESOURCE_URI}}|$openAIServiceAccountEndpoint|; \
                  s|{{VECTORIZER_API_KEY}}|$openAIServiceAccountKey|; \
                  s|{{VECTORIZER_DEPLOYMENT_ID}}|$openAIServiceEmbeddingsDeployName|;" \
                  "search_index.json")"
