
from germansentiment import SentimentModel
import requests
import matplotlib.pyplot as plt


class Speech:
    speech_raw_json = None

    # Sentence has the format {"text": "text", "timeStart": "timeStart", "timeEnd": "timeEnd", "type": "type", "duration": "duration"}
    sentences = None

    # metadata has the format {"duration": "duration", "date_start": "date_start", "date_end": "date_end"}
    speech_metadata = None

    sentiment_model = None

    def __init__(self, url):
        self.speech_raw_json = requests.get(url).json()
        self.sentences = self.__parse_sentences()
        self.speech_metadata = self.__parse_speech_metadata()
        self.sentiment_model = SentimentModel()
        self.__analyse_sentiment()

    def __parse_speech_metadata(self):
        speech_metadata = {}
        speech_metadata["duration"] = self.speech_raw_json["data"]["attributes"]["duration"]
        speech_metadata["date_start"] = self.speech_raw_json["data"]["attributes"]["dateStart"]
        speech_metadata["date_end"] = self.speech_raw_json["data"]["attributes"]["dateEnd"]

        return speech_metadata

    def __parse_sentences(self):
        speech_excerpts_with_metadata = self.speech_raw_json[
            "data"]["attributes"]["textContents"][0]["textBody"]

        speech_sentences_with_timestamps = []

        for speech_excerpt_with_metadata in speech_excerpts_with_metadata:
            speech_excerpt_sentences = speech_excerpt_with_metadata["sentences"]
            for speech_excerpt_sentence in speech_excerpt_sentences:
                speech_excerpt_sentence["type"] = speech_excerpt_with_metadata["type"]
                speech_excerpt_sentence["duration"] = self.__calculate_sentence_length_seconds(
                    speech_excerpt_sentence)
                speech_excerpt_sentence["sentiment_score"] = None
                speech_excerpt_sentence["sentiment_positive_weight"] = None
                speech_excerpt_sentence["sentiment_negative_weight"] = None
                speech_excerpt_sentence["sentiment_neutral_weight"] = None

            speech_sentences_with_timestamps.extend(
                speech_excerpt_sentences)

        return speech_sentences_with_timestamps

    def __analyse_sentiment(self):
        sentences_text = [sentence["text"] for sentence in self.sentences]
        result = self.sentiment_model.predict_sentiment(
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

    def get_sentences_by_type(self, type):
        if type not in ["speech", "comment"]:
            raise ValueError("Invalid type")
        sentences_filtered_by_type = []
        for sentence in self.sentences:
            if sentence["type"] == type:
                sentences_filtered_by_type.append(sentence)
        return sentences_filtered_by_type

    def __calculate_sentence_length_seconds(self, sentence):
        # The timestamps are in seconds with 3 decimal places and are strings
        timeEnd = float(sentence["timeEnd"])
        timeStart = float(sentence["timeStart"])

        # Should return to 3dp
        return timeEnd - timeStart


def main():
    speech_url = "https://de.openparliament.tv/api/v1/media/DE-0200087057"

    speech = Speech(speech_url)

    # This removes the "comments" which are the "Zwischenrufe" - i.e. the heckling
    sentences = speech.get_sentences_by_type("speech")

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

    print("Total duration: " + str(total_duration))

    print("Duration positive: " + str(duration_postive))
    print("Duration neutral: " + str(duration_neutral))
    print("Duration negative: " + str(duration_negative))

    print("Percentage positive: " + str(duration_postive / total_duration))
    print("Percentage neutral: " + str(duration_neutral / total_duration))
    print("Percentage negative: " + str(duration_negative / total_duration))
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
