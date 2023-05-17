
import os
from germansentiment import SentimentModel
from categorised_speech_group import CategorisedSpeechGroup
from speech import Speech
import requests
import pandas as pd
import urllib.parse
from datetime import datetime
import matplotlib.pyplot as plt

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
    if "data" not in speeches_raw_json:
        print("No speeches found for query " + query)
        return speeches

    for speech_data in speeches_raw_json["data"]:
        if limit is not None and current_speech >= limit:
            break
        current_speech += 1
        speech_data_formatted = {}
        speech_data_formatted["data"] = speech_data

        speech = Speech(speech_raw_json=speech_data_formatted)
        speech.set_keyword(query)
        speeches.append(speech)

    return speeches


def main():
    # keywords = ["Ausländer",
    #             "Budget", "Covid",
    #             "Europäische Union", "Gesundheit"]

    keywords = ["Covid"]

    speeches_per_keyword = 5

    sentiment_model = SentimentModel()

    date_start = datetime(2022, 1, 1)
    date_end = datetime(2023, 5, 1)

    # make directory to output all results
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    results_dir = "./results/" + timestamp
    os.mkdir(results_dir)

    all_speeches = []
    for faction in faction_ids:
        faction_label = faction
        faction_id = faction_ids[faction]
        for keyword in keywords:
            print("Getting speeches for keyword " +
                  keyword + " and faction " + faction_label)
            speeches = get_speeches_by_query(
                keyword, speeches_per_keyword, date_start, date_end, faction_id)
            all_speeches += speeches

    all_speech_summaries = pd.DataFrame()

    for speech in all_speeches:
        speech.analyse_sentiment(sentiment_model)
        speech_summary = speech.generate_summary()
        if speech_summary is not None:
            # Delete speech if it has no sentences, this is caused by their being no main speaker
            speech.write_speech_df_to_csv(
                results_dir + "/" + speech.get_id() + ".csv")
            all_speech_summaries = pd.concat([all_speech_summaries, speech_summary],
                                             ignore_index=False)

    all_speech_summaries.to_csv(results_dir + "/master_summary.csv")

    # Now create a scatter plot using the postive and negative percent scores, each party should have a different colour with a single dot for each speech
    unique_factions = all_speech_summaries["main_speaker_faction"].unique()
    colors = iter([plt.cm.tab20(i) for i in range(20)])

    for unique_faction in unique_factions:
        faction_speeches = all_speech_summaries[all_speech_summaries["main_speaker_faction"]
                                                == unique_faction]
        plt.scatter(x=faction_speeches["speech_positive_percentage"], y=faction_speeches["speech_negative_percentage"],
                    c=[next(colors)], label=unique_faction)

    # set axes to 0.2 and 0.2
    plt.xlim(right=0.2)
    plt.ylim(top=0.2)

    plt.legend()
    plt.xlabel("Percentage of speech that is positive")
    plt.ylabel("Percentage of speech that is negative")

    plt.savefig(results_dir + "/scatter_plot.png")

    plt.show()


if __name__ == "__main__":
    main()
