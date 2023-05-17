import requests
import json
import pandas as pd


class Speech:
    speech_raw_json = None
    sentiment_model = None
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
        self.speech_raw_json = requests.get(url).json()

    def __init_from_speech_raw_json(self, speech_raw_json):
        self.speech_raw_json = speech_raw_json

    def __parse_speech(self):
        speech_df = pd.DataFrame()

        raw_speech_excerpts = self.speech_raw_json[
            "data"]["attributes"]["textContents"][0]["textBody"]

        for raw_speech_excerpt in raw_speech_excerpts:
            speech_excerpt_sentences = raw_speech_excerpt["sentences"]
            for speech_excerpt_sentence in speech_excerpt_sentences:
                # The id of the speech in the database
                speech_id = raw_speech_excerpt["speech_id"]

                # The api url of the speech
                speech_url = self.speech_raw_json["data"]["links"]["self"]

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
                    "speech_url": speech_url,
                    "speech_keyword": None,
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
            self.speech_df.at[i, "sentence_sentiment_score"] = sentiment_score
            # Positive is the 0th element, the weighting is always the 1st
            self.speech_df.at[i,
                              "sentence_sentiment_positive_weight"] = sentiment_weights[i][0][1]
            # Negative is the 1st element, the weighting is always the 1st
            self.speech_df.at[i,
                              "sentence_sentiment_negative_weight"] = sentiment_weights[i][1][1]
            # Neutral is the 2nd element, the weighting is always the 1st
            self.speech_df.at[i,
                              "sentence_sentiment_neutral_weight"] = sentiment_weights[i][2][1]

    def generate_summary(self):
        # Need to get the postive, negative, and neutral durations as well as filter by main speaker
        # First we need to filter the dataframe to only get the mainspeaker's sentence results
        speech_summary_df = self.speech_df[self.speech_df['sentence_speaker_status']
                                           == "main-speaker"]
        if speech_summary_df.empty:
            print("No main speaker found for speech id " + self.get_id())
            return None

        try:
            speech_metadata = speech_summary_df[["speech_id", "speech_url", "speech_keyword", "speech_duration", "speech_date_start", "speech_date_end",
                                                 "speech_agenda_item_title", "sentence_speaker", "sentence_speaker_status", "sentence_speaker_party", "sentence_speaker_faction"]].iloc[0]
        except:
            print("error parsing speech metadata for speech id " + self.get_id())
            print(speech_summary_df)
            raise ValueError(
                "error parsing speech metadata for speech id " + self.get_id())

        speech_summary_df = speech_summary_df[[
            "sentence_sentiment_score", "sentence_duration"]]

        speech_summary_df_grouped = speech_summary_df.groupby(
            ["sentence_sentiment_score"]).sum()

        if "positive" not in speech_summary_df_grouped.index:
            speech_summary_df_grouped.at["positive", "sentence_duration"] = 0
        if "negative" not in speech_summary_df_grouped.index:
            speech_summary_df_grouped.at["negative", "sentence_duration"] = 0
        if "neutral" not in speech_summary_df_grouped.index:
            speech_summary_df_grouped.at["neutral", "sentence_duration"] = 0

        speech_summary_df_grouped["percentage"] = speech_summary_df_grouped["sentence_duration"] / \
            speech_summary_df_grouped["sentence_duration"].sum()

        try:
            speech_negative_duration = speech_summary_df_grouped.at["negative",
                                                                    "sentence_duration"]
            speech_negative_percentage = speech_summary_df_grouped.at["negative",
                                                                      "percentage"]
            speech_neutral_duration = speech_summary_df_grouped.at["neutral",
                                                                   "sentence_duration"]
            speech_neutral_percentage = speech_summary_df_grouped.at["neutral",
                                                                     "percentage"]
            speech_positive_duration = speech_summary_df_grouped.at["positive",
                                                                    "sentence_duration"]
            speech_positive_percentage = speech_summary_df_grouped.at["positive",
                                                                      "percentage"]
        except:
            print("error parsing speech summary for speech id " + self.get_id())
            print(speech_summary_df_grouped)
            raise ValueError(
                "error parsing speech summary for speech id " + self.get_id())

        speech_summary_final_df = pd.DataFrame({
            "speech_id": speech_metadata["speech_id"],
            "speech_url": speech_metadata["speech_url"],
            "speech_duration": speech_metadata["speech_duration"],
            "speech_keyword": speech_metadata["speech_keyword"],
            "speech_date_start": speech_metadata["speech_date_start"],
            "speech_date_end": speech_metadata["speech_date_end"],
            "speech_agenda_item_title": speech_metadata["speech_agenda_item_title"],
            "main_speaker": speech_metadata["sentence_speaker"],
            "main_speaker_party": speech_metadata["sentence_speaker_party"],
            "main_speaker_faction": speech_metadata["sentence_speaker_faction"],
            "speech_negative_duration": speech_negative_duration,
            "speech_negative_percentage": speech_negative_percentage,
            "speech_neutral_duration": speech_neutral_duration,
            "speech_neutral_percentage": speech_neutral_percentage,
            "speech_positive_duration": speech_positive_duration,
            "speech_positive_percentage": speech_positive_percentage
        }, index=[0])
        speech_summary_final_df.set_index("speech_id", inplace=True)
        return speech_summary_final_df

    def get_speech_df(self):
        return self.speech_df

    def write_speech_df_to_csv(self, filename_with_directory):
        self.speech_df.to_csv(filename_with_directory, index=False)

    def set_keyword(self, keyword):
        self.speech_df["speech_keyword"] = keyword

    def get_id(self):
        return self.speech_df["speech_id"].iloc[0]
