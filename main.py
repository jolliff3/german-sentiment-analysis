
from germansentiment import SentimentModel
import requests
import matplotlib.pyplot as plt
import csv
import json


class Speech:
    speech_raw_json = None

    # Sentence has the format {"text": "text", "timeStart": "timeStart", "timeEnd": "timeEnd", "type": "type", "duration": "duration"}
    sentences = None

    # metadata has the format {"duration": "duration", "date_start": "date_start", "date_end": "date_end"}
    speech_metadata = None

    sentiment_model = None
    api_url = None

    def __init__(self, url=None, speech_raw_json=None):
        if url is None and speech_raw_json is None:
            raise ValueError("Must provide either url or speech_raw_json")
        if url is not None and speech_raw_json is not None:
            raise ValueError(
                "Must provide either url or speech_raw_json, not both")
        if url is not None:
            self.__init_from_url(url)
        else:
            self.__init_from_speech_raw_json(speech_raw_json)

        self.sentences = self.__parse_sentences()
        self.speech_metadata = self.__parse_speech_metadata()

    def __init_from_url(self, url):
        self.api_url = url
        self.speech_raw_json = requests.get(self.api_url).json()

    def __init_from_speech_raw_json(self, speech_raw_json):
        self.speech_raw_json = speech_raw_json
        self.api_url = "unknown"

    def __parse_speech_metadata(self):
        speech_metadata = {}
        speech_metadata["api_url"] = self.api_url
        speech_metadata["duration"] = self.speech_raw_json["data"]["attributes"]["duration"]
        speech_metadata["date_start"] = self.speech_raw_json["data"]["attributes"]["dateStart"]
        speech_metadata["date_end"] = self.speech_raw_json["data"]["attributes"]["dateEnd"]
        speech_metadata["agenda_item_official_title"] = self.speech_raw_json["data"][
            "relationships"]["agendaItem"]["data"]["attributes"]["officialTitle"]
        speech_metadata["agenda_item_title"] = self.speech_raw_json["data"]["relationships"]["agendaItem"]["data"]["attributes"]["title"]
        # To find the main speaker, we itterate through the sentences until we find the first one with the speaker status "main-speaker"
        for sentence in self.sentences:
            if sentence["speaker_status"] == "main-speaker":
                if sentence["speaker"] is None:
                    speech_metadata["main_speaker"] = "unknown"
                else:
                    speech_metadata["main_speaker"] = sentence["speaker"]
                break

        if "main_speaker" not in speech_metadata:
            speech_metadata["main_speaker"] = "unknown"

        # Find the person data using the speech_metadata["main_speaker"]
        if speech_metadata["main_speaker"] == "unknown":
            speech_metadata["main_speaker_party"] = "unknown"
        else:
            for person in self.speech_raw_json["data"]["relationships"]["people"]["data"]:
                if person["attributes"]["label"] == speech_metadata["main_speaker"]:
                    speech_metadata["main_speaker_party"] = person["attributes"]["party"]["label"]
                    break

        return speech_metadata

    def __parse_sentences(self):
        speech_excerpts_with_metadata = self.speech_raw_json[
            "data"]["attributes"]["textContents"][0]["textBody"]

        speech_sentences_with_timestamps = []

        for speech_excerpt_with_metadata in speech_excerpts_with_metadata:
            speech_excerpt_sentences = speech_excerpt_with_metadata["sentences"]
            for speech_excerpt_sentence in speech_excerpt_sentences:
                speech_excerpt_sentence["type"] = speech_excerpt_with_metadata["type"]

                if "timeStart" not in speech_excerpt_sentence:
                    speech_excerpt_sentence["timeStart"] = 0
                if "timeEnd" not in speech_excerpt_sentence:
                    speech_excerpt_sentence["timeEnd"] = 0
                speech_excerpt_sentence["duration"] = self.__calculate_sentence_length_seconds(
                    speech_excerpt_sentence)

                # The name of the speaker, e.g. "Martin Sichert"
                speech_excerpt_sentence["speaker"] = speech_excerpt_with_metadata["speaker"]
                # e.g. "president" or "main-speaker", "null" for general comments
                speech_excerpt_sentence["speaker_status"] = speech_excerpt_with_metadata["speakerstatus"]

                # These are the sentiment scores initialised as None
                speech_excerpt_sentence["sentiment_score"] = None
                speech_excerpt_sentence["sentiment_positive_weight"] = None
                speech_excerpt_sentence["sentiment_negative_weight"] = None
                speech_excerpt_sentence["sentiment_neutral_weight"] = None

            speech_sentences_with_timestamps.extend(
                speech_excerpt_sentences)

        return speech_sentences_with_timestamps

    def analyse_sentiment(self, sentiment_model):
        sentences_text = [sentence["text"] for sentence in self.sentences]
        result = sentiment_model.predict_sentiment(
            sentences_text, True)
        sentiment_scores = result[0]
        sentiment_weights = result[1]

        for i, sentiment_score in enumerate(sentiment_scores):
            self.sentences[i]["sentiment_score"] = sentiment_score
            # Positive is the 0th element, the weighting is always the 1st
            self.sentences[i]["sentiment_positive_weight"] = sentiment_weights[i][0][1]
            # Negative is the 1st element, the weighting is always the 1st
            self.sentences[i]["sentiment_negative_weight"] = sentiment_weights[i][1][1]
            # Neutral is the 2nd element, the weighting is always the 1st
            self.sentences[i]["sentiment_neutral_weight"] = sentiment_weights[i][2][1]

    def __calculate_sentence_length_seconds(self, sentence):
        # The timestamps are in seconds with 3 decimal places and are strings
        try:
            timeEnd = float(sentence["timeEnd"])
            timeStart = float(sentence["timeStart"])
        except:
            print("invalid sentence: " + json.dumps(sentence))
            raise ValueError("Invalid sentence")

        # Should return to 3dp
        return timeEnd - timeStart

    def get_sentences_by_type(self, type):
        if type not in ["speech", "comment"]:
            raise ValueError("Invalid type")
        sentences_filtered_by_type = []
        for sentence in self.sentences:
            if sentence["type"] == type:
                sentences_filtered_by_type.append(sentence)
        return sentences_filtered_by_type

    def get_sentences_by_speaker_status(self, speaker_status):
        if speaker_status not in ["president", "main-speaker"]:
            raise ValueError("Invalid speaker status")
        sentences_filtered_by_speaker_status = []
        for sentence in self.sentences:
            if sentence["speaker_status"] == speaker_status:
                sentences_filtered_by_speaker_status.append(sentence)

        return sentences_filtered_by_speaker_status

    def get_speech_metadata(self):
        return self.speech_metadata


def analyse_speech(speech, sentiment_model):
    speech.analyse_sentiment(sentiment_model)

    sentences = speech.get_sentences_by_speaker_status("main-speaker")

    total_duration = 0
    duration_postive = 0
    duration_neutral = 0
    duration_negative = 0

    for sentence in sentences:
        total_duration += sentence["duration"]
        if sentence["sentiment_score"] == "positive":
            duration_postive += sentence["duration"]
        elif sentence["sentiment_score"] == "neutral":
            duration_neutral += sentence["duration"]
        elif sentence["sentiment_score"] == "negative":
            duration_negative += sentence["duration"]
        else:
            raise ValueError("Invalid sentiment score")

    metadata = speech.get_speech_metadata()

    analysis_results = {
        "total_duration": total_duration,
        "duration_postive": duration_postive,
        "duration_neutral": duration_neutral,
        "duration_negative": duration_negative,
        "agenda_item_title": metadata["agenda_item_title"],
        "main_speaker": metadata["main_speaker"],
        "main_speaker_party": metadata["main_speaker_party"],
    }

    if total_duration != 0:
        analysis_results["percentage_positive"] = duration_postive / \
            total_duration
        analysis_results["percentage_neutral"] = duration_neutral / \
            total_duration
        analysis_results["percentage_negative"] = duration_negative / \
            total_duration
    else:
        analysis_results["percentage_positive"] = 0
        analysis_results["percentage_neutral"] = 0
        analysis_results["percentage_negative"] = 0
    return analysis_results


def create_csv_from_analysis_results(array_of_analysis_results, filename="results.csv"):
    path = "results/" + filename

    with open(path, 'w', newline='') as file:
        writer = csv.writer(file)
        field = ["total_duration", "duration_postive", "duration_neutral", "duration_negative",
                 "percentage_positive", "percentage_neutral", "percentage_negative", "agenda_item_title", "main_speaker", "main_speaker_party"]
        writer.writerow(field)
        for analysis_result in array_of_analysis_results:
            writer.writerow([analysis_result["total_duration"], analysis_result["duration_postive"], analysis_result["duration_neutral"],
                             analysis_result["duration_negative"], analysis_result[
                                 "percentage_positive"], analysis_result["percentage_neutral"],
                             analysis_result["percentage_negative"], analysis_result["agenda_item_title"], analysis_result["main_speaker"], analysis_result["main_speaker_party"]])


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
    # speeches = get_speeches_by_query("Ausländer", 20)
    speeches = get_speeches_by_query("Budget", 20)
    sentiment_model = SentimentModel()

    array_of_analysis_results = []

    for speech in speeches:
        analysis_results = analyse_speech(speech, sentiment_model)
        array_of_analysis_results.append(analysis_results)
        print(speech.get_speech_metadata())

    create_csv_from_analysis_results(array_of_analysis_results, "budget_query_results.csv")

    # sentiment_model = SentimentModel()
    # speech_urls = [
    #     # Martin SichertAfD - Impfpflicht gegen SARS-CoV-2 https://de.openparliament.tv/media/DE-0200028012?q=AFD&factionID%5B%5D=Q42575708
    #     "https://de.openparliament.tv/api/v1/media/DE-0200028012",
    #     # Nicole HöchstAfD - Akademische und berufliche Bildung https://de.openparliament.tv/media/DE-0200103063?q=AFD&factionID%5B%5D=Q42575708
    #     "https://de.openparliament.tv/api/v1/media/DE-0200103063",
    #     # Gottfried CurioAfD - Durchsetzung des Asyl- und Aufenthaltsrechts https://de.openparliament.tv/media/DE-0200103033?q=AFD&factionID%5B%5D=Q42575708
    #     "https://de.openparliament.tv/api/v1/media/DE-0200103033",
    #     # NOT AFD https://de.openparliament.tv/api/v1/media/DE-0190204119
    #     "https://de.openparliament.tv/api/v1/media/DE-0190204119",
    #     # Martin HessAfD - Kriminalität in Bahnhöfen und Zügen https://de.openparliament.tv/media/DE-0200087057?q=Jahr+2022+um+38%2C6%25+von+rund&factionID%5B%5D=Q42575708&dateFrom=2022-10-15
    #     "https://de.openparliament.tv/api/v1/media/DE-0200087057",
    #     # Lamya KaddorDIE GRÜNEN - Clankriminalität
    #     "https://de.openparliament.tv/api/v1/media/DE-0200033073",
    #     # Peggy SchierenbeckSPD - Kriminalität in Bahnhöfen und Zügen
    #     "https://de.openparliament.tv/api/v1/media/DE-0200087058",
    # ]

    # array_of_analysis_results = []

    # for speech_url in speech_urls:
    #     speech = Speech(url=speech_url)
    #     analysis_results = analyse_speech(speech, sentiment_model)
    #     array_of_analysis_results.append(analysis_results)
    #     print("Analysis results for speech: " + speech_url)
    #     print(analysis_results)

    # create_csv_from_analysis_results(array_of_analysis_results)

    # # Now to make a plot!

    # x = []
    # y = []

    # for speech_sentence_with_timestamp in main_speaker_sentences:
    #     x.append(speech_sentence_with_timestamp["timeStart"])
    #     y.append(speech_sentence_with_timestamp["sentiment_score"])
    #     x.append(speech_sentence_with_timestamp["timeEnd"])
    #     y.append(speech_sentence_with_timestamp["sentiment_score"])

    # plt.plot(x, y)
    # plt.show()


if __name__ == "__main__":
    main()
