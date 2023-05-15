
from germansentiment import SentimentModel
from categorised_speech_group import CategorisedSpeechGroup
from speech import Speech
import requests
import pandas as pd


def get_speeches_by_query(query, limit=None):
    base_url = "https://de.openparliament.tv/api/v1/search/media"
    query_url = base_url + "?q=" + query
    speeches_raw_json = requests.get(query_url).json()
    speeches = []

    current_speech = 0
    for speech_data in speeches_raw_json["data"]:
        if limit is not None and current_speech >= limit:
            break
        current_speech += 1
        speech_data_formatted = {}
        speech_data_formatted["data"] = speech_data

        speeches.append(Speech(speech_raw_json=speech_data_formatted))

    return speeches


def main():
    sentiment_model = SentimentModel()

    auslander_speeches = get_speeches_by_query("Ausländer", 20)
    budget_speeches = get_speeches_by_query("Budget", 20)

    auslander_speech_group = CategorisedSpeechGroup(
        auslander_speeches, "Ausländer")

    budget_speech_group = CategorisedSpeechGroup(
        budget_speeches, "Budget")

    budget_speech_group.analyse_speeches(sentiment_model)
    budget_speech_group.generate_report()

    auslander_speech_group.analyse_speeches(sentiment_model)
    auslander_speech_group.generate_report()


if __name__ == "__main__":
    main()
