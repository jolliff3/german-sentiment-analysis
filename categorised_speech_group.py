from speech import Speech
import pandas as pd
from datetime import datetime


class CategorisedSpeechGroup:
    categorised_speeches = None
    category_label = None
    analysis_results = None

    def __init__(self, categorised_speeches, category_label):
        self.categorised_speeches = categorised_speeches
        self.category_label = category_label

    def analyse_speeches(self, sentiment_model):
        self.analysis_results = pd.DataFrame()
        for categorised_speech in self.categorised_speeches:
            analysis = self.__analyse_speech(
                categorised_speech, sentiment_model)
            analysis["category"] = self.category_label

            analysis_dataframe = pd.DataFrame(analysis, index=[0])
            self.analysis_results = pd.concat(
                [self.analysis_results, analysis_dataframe])

    def get_results_grouped_by_party(self):
        if self.analysis_results is None:
            raise ValueError("Must analyse speeches before getting results")

        results_df_grouped = self.analysis_results[["main_speaker_party", "total_duration", "duration_positive",
                                                    "duration_neutral", "duration_negative"]].groupby(["main_speaker_party"]).sum()

        results_df_grouped["percentage_positive"] = results_df_grouped["duration_positive"] / \
            results_df_grouped["total_duration"]
        results_df_grouped["percentage_neutral"] = results_df_grouped["duration_neutral"] / \
            results_df_grouped["total_duration"]
        results_df_grouped["percentage_negative"] = results_df_grouped["duration_negative"] / \
            results_df_grouped["total_duration"]

        return results_df_grouped

    def generate_report(self):
        if self.analysis_results is None:
            raise ValueError("Must analyse speeches before generating report")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        grouped_by_party = self.get_results_grouped_by_party()
        grouped_by_party["category"] = self.category_label
        grouped_by_party.to_csv(
            "results/" + self.category_label + "_grouped_by_party"+timestamp+".csv")

    def __analyse_speech(self, speech: Speech, sentiment_model):
        speech.analyse_sentiment(sentiment_model)

        sentences = speech.get_sentences_by_speaker_status("main-speaker")

        total_duration = 0
        duration_positive = 0
        duration_neutral = 0
        duration_negative = 0

        for sentence in sentences:
            total_duration += sentence["duration"]
            if sentence["sentiment_score"] == "positive":
                duration_positive += sentence["duration"]
            elif sentence["sentiment_score"] == "neutral":
                duration_neutral += sentence["duration"]
            elif sentence["sentiment_score"] == "negative":
                duration_negative += sentence["duration"]
            else:
                raise ValueError("Invalid sentiment score")

        metadata = speech.get_speech_metadata()

        analysis_results = {
            "total_duration": total_duration,
            "duration_positive": duration_positive,
            "duration_neutral": duration_neutral,
            "duration_negative": duration_negative,
            "agenda_item_title": metadata["agenda_item_title"],
            "main_speaker": metadata["main_speaker"],
            "main_speaker_party": metadata["main_speaker_party"],
        }

        if total_duration != 0:
            analysis_results["percentage_positive"] = duration_positive / \
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
