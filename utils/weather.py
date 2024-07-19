import requests


def get_weather_in_tokyo() -> dict:
    """
    東京の天気情報を取得する

    Returns:
        dict: 天気情報
    """
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/010000.json"
    weather = requests.get(url).json()
    weather = [w for w in weather if w["name"] == "東京"][0]
    return weather
