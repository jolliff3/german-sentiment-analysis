
from germansentiment import SentimentModel
from categorised_speech_group import CategorisedSpeechGroup
from speech import Speech
import requests
import pandas as pd
import urllib.parse
from datetime import datetime

faction_ids = {
    "CDU/CSU": "Q1023134",
    "SPD": "Q2207512",
    "AfD": "Q42575708",
    "FDP": "Q1387991",
    "DIE LINKE": "Q1826856",
    "DIE GRÜNEN": "Q1007353",
    "fraktionslos": "Q4316268",
}


def get_timestamp_from_datetime(dt):
    epoch = datetime.utcfromtimestamp(0)
    return int((dt - epoch).total_seconds() * 1000.0)


def get_speeches_by_query(query, limit=None, date_start=None, date_end=None, faction_id=None):
    base_url = "https://de.openparliament.tv/api/v1/search/media"
    parsed_query = urllib.parse.quote(query)
    print(parsed_query)
    query_url = base_url + "?q=" + parsed_query
    if date_start is not None:
        date_start_millis = get_timestamp_from_datetime(
            date_start)
        date_start_string = str(date_start_millis)
        query_url += "&dateFrom=" + date_start_string
    if date_end is not None:
        date_end_millis = get_timestamp_from_datetime(
            date_end)
        date_end_string = str(date_end_millis)
        query_url += "&dateTo=" + date_end_string
    if faction_id is not None:
        query_url += "&factionID=" + urllib.parse.quote(faction_id)
    print(query_url)
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
    keywords = ["Ausländer", "Budget", "Covid",
                "Europäische Union", "Gesundheit"]

    speeches_per_keyword = 5

    sentiment_model = SentimentModel()

    date_start = datetime(2022, 1, 1)
    date_end = datetime(2023, 5, 1)

    speech_groups = []

    # for faction in faction_ids:
    #     faction_label = faction
    #     faction_id = faction_ids[faction]
    #     for keyword in keywords:
    #         print("Getting speeches for keyword " +
    #               keyword + " and faction " + faction_label)
    #         speeches = get_speeches_by_query(
    #             keyword, speeches_per_keyword, date_start, date_end, faction_id)
    #         speech_group = CategorisedSpeechGroup(
    #             speeches, keyword, faction_label)
    #         speech_group.analyse_speeches(sentiment_model)
    #         speech_groups.append(speech_group)
    speeches = get_speeches_by_query(
        "Ausländer", 5, date_start, date_end, faction_ids["AfD"])

    speeches[0].analyse_sentiment(sentiment_model)
    test_df = speeches[0].get_speech_df()
    print(test_df)

    test_df.to_csv("test.csv")

    # auslander_speeches = get_speeches_by_query(
    #     "Ausländer", 20, date_start, date_end, faction_ids["AfD"])
    # budget_speeches = get_speeches_by_query(
    #     "Budget", 20, date_start, date_end, faction_ids["AfD"])
    # covid_speeches = get_speeches_by_query(
    #     "Covid", 20, date_start, date_end, faction_ids["AfD"])
    # europaische_union_speeches = get_speeches_by_query(
    #     "Europäische Union", 20, date_start, date_end, faction_ids["AfD"])

    # auslander_speech_group = CategorisedSpeechGroup(
    #     auslander_speeches, "Ausländer")

    # budget_speech_group = CategorisedSpeechGroup(
    #     budget_speeches, "Budget")

    # covid_speech_group = CategorisedSpeechGroup(
    #     covid_speeches, "Covid")

    # europaische_union_speech_group = CategorisedSpeechGroup(
    #     europaische_union_speeches, "Europäische Union")

    # budget_speech_group.analyse_speeches(sentiment_model)
    # budget_speech_group.generate_report()

    # auslander_speech_group.analyse_speeches(sentiment_model)
    # auslander_speech_group.generate_report()

    # covid_speech_group.analyse_speeches(sentiment_model)
    # covid_speech_group.generate_report()

    # europaische_union_speech_group.analyse_speeches(sentiment_model)
    # europaische_union_speech_group.generate_report()


if __name__ == "__main__":
    main()
