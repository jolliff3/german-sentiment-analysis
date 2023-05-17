import requests
import json
import pandas as pd


class Speech:
    speech_raw_json = None

    # Sentence has the format {"text": "text", "timeStart": "timeStart", "timeEnd": "timeEnd", "type": "type", "duration": "duration"}
    sentences = None

    # metadata has the format {"duration": "duration", "date_start": "date_start", "date_end": "date_end"}
    speech_metadata = None

    sentiment_model = None
    api_url = None
    speech_df = None

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

        self.speech_df = self.__parse_speech()

    def __init_from_url(self, url):
        self.api_url = url
        self.speech_raw_json = requests.get(self.api_url).json()

    def __init_from_speech_raw_json(self, speech_raw_json):
        self.speech_raw_json = speech_raw_json
        self.api_url = "unknown"

    def __parse_speech(self):
        speech_df = pd.DataFrame()

        raw_speech_excerpts = self.speech_raw_json[
            "data"]["attributes"]["textContents"][0]["textBody"]

        for raw_speech_excerpt in raw_speech_excerpts:
            speech_excerpt_sentences = raw_speech_excerpt["sentences"]
            for speech_excerpt_sentence in speech_excerpt_sentences:
                # The id of the speech in the database
                speech_id = raw_speech_excerpt["speech_id"]

                # The total speech duration, including comments and other non speech sentences
                speech_duration = self.speech_raw_json["data"]["attributes"]["duration"]

                # The start date/time of the speech. This is a string
                speech_date_start = self.speech_raw_json["data"]["attributes"]["dateStart"]

                # The end date/time of the speech. This is a string
                speech_date_end = self.speech_raw_json["data"]["attributes"]["dateEnd"]

                # Speech agenda item title
                speech_agenda_item_title = self.speech_raw_json["data"][
                    "relationships"]["agendaItem"]["data"]["attributes"]["officialTitle"]

                # The speaker of the sentence note: this can be null
                sentence_speaker = raw_speech_excerpt["speaker"]

                # The status of the speaker, e.g. "president" or "main-speaker", note: this can be null
                sentence_speaker_status = raw_speech_excerpt["speakerstatus"]

                # The type of the sentence, e.g. "speech" or "comment"
                sentence_type = raw_speech_excerpt["type"]

                # The text of the sentence
                sentence_text = speech_excerpt_sentence["text"]

                # sentence start time in seconds
                if "timeStart" not in speech_excerpt_sentence:
                    sentence_time_start = 0
                else:
                    sentence_time_start = float(
                        speech_excerpt_sentence["timeStart"])

                # sentence end time in seconds
                if "timeEnd" not in speech_excerpt_sentence:
                    sentence_time_end = 0
                else:
                    sentence_time_end = float(
                        speech_excerpt_sentence["timeEnd"])

                # the sentence duration in seconds (end - start)
                sentence_duration = sentence_time_end - sentence_time_start

                for person in self.speech_raw_json["data"]["relationships"]["people"]["data"]:
                    if sentence_speaker == None:
                        sentence_speaker_party = None
                        sentence_speaker_faction = None
                        break
                    elif person["attributes"]["label"] == sentence_speaker:
                        sentence_speaker_party = person["attributes"]["party"]["label"]
                        sentence_speaker_faction = person["attributes"]["faction"]["label"]
                        break
                    elif sentence_speaker in person["attributes"]["labelAlternative"]:
                        sentence_speaker_party = person["attributes"]["party"]["label"]
                        sentence_speaker_faction = person["attributes"]["faction"]["label"]
                        break
                    else:
                        sentence_speaker_party = None
                        sentence_speaker_faction = None

                # These are the sentiment scores initialised as None
                sentence_sentiment_score = None
                sentence_sentiment_positive_weight = None
                sentence_sentiment_negative_weight = None
                sentence_sentiment_neutral_weight = None

                # This is the dictionary that will be appended to the dataframe
                speech_excerpt_sentence_dict = {
                    "speech_id": speech_id,
                    "speech_duration": speech_duration,
                    "speech_date_start": speech_date_start,
                    "speech_date_end": speech_date_end,
                    "speech_agenda_item_title": speech_agenda_item_title,
                    "sentence_speaker": sentence_speaker,
                    "sentence_speaker_status": sentence_speaker_status,
                    "sentence_speaker_party": sentence_speaker_party,
                    "sentence_speaker_faction": sentence_speaker_faction,
                    "sentence_type": sentence_type,
                    "sentence_text": sentence_text,
                    "sentence_time_start": sentence_time_start,
                    "sentence_time_end": sentence_time_end,
                    "sentence_duration": sentence_duration,
                    "sentence_sentiment_score": sentence_sentiment_score,
                    "sentence_sentiment_positive_weight": sentence_sentiment_positive_weight,
                    "sentence_sentiment_negative_weight": sentence_sentiment_negative_weight,
                    "sentence_sentiment_neutral_weight": sentence_sentiment_neutral_weight
                }

                sentence_df = pd.DataFrame(
                    speech_excerpt_sentence_dict, index=[0])

                speech_df = pd.concat([speech_df, sentence_df],
                                      ignore_index=True)

        return speech_df

    def analyse_sentiment(self, sentiment_model):
        sentences_text_numpy_array = self.speech_df["sentence_text"].to_numpy()
        sentences_text_array = sentences_text_numpy_array.tolist()

        result = sentiment_model.predict_sentiment(
            sentences_text_array, True)

        sentiment_scores = result[0]
        sentiment_weights = result[1]

        for i, sentiment_score in enumerate(sentiment_scores):
            self.speech_df["sentence_sentiment_score"][i] = sentiment_score
            # Positive is the 0th element, the weighting is always the 1st
            self.speech_df["sentence_sentiment_positive_weight"][i] = sentiment_weights[i][0][1]
            # Negative is the 1st element, the weighting is always the 1st
            self.speech_df["sentence_sentiment_negative_weight"][i] = sentiment_weights[i][1][1]
            # Neutral is the 2nd element, the weighting is always the 1st
            self.speech_df["sentence_sentiment_neutral_weight"][i] = sentiment_weights[i][2][1]

    def get_speech_df(self):
        return self.speech_df
