from speech import Speech
import pandas as pd
from datetime import datetime


class CategorisedSpeechGroup:
    categorised_speeches = None
    keyword = None
    faction = None
    analysis_results = None

    def __init__(self, categorised_speeches, keyword, faction="Unknown"):
        self.categorised_speeches = categorised_speeches
        self.keyword = keyword
        self.faction = faction

    def analyse_speeches(self, sentiment_model):
        all_speech_df = pd.DataFrame()
        for speech in self.categorised_speeches:
            # analyse_sentiment sets the speech's sentiment_score and other columns (initiated as None)
            speech.analyse_sentiment(sentiment_model)

            # Now that the sentiment scores have been added to the dataframe, we can get the df
            speech_df = speech.get_speech_df()

            # We now create one big dataframe with all the speeches so we can analysise them together
            all_speech_df = pd.concat([all_speech_df, speech_df],
                                      ignore_index=True)

        # Now we need to filter the dataframe to only get the mainspeaker's sentence results, and group the scores
        main_speaker_sentences = all_speech_df[all_speech_df['sentence_speaker_status']
                                               == "main-speaker"]

        # now we need to group by the main speaker's faction, party, agenda item title, and main speaker
        main_speaker_sentences_grouped = main_speaker_sentences.groupby(
            ["sentence_speaker_faction", "sentence_speaker_party", "speech_agenda_item_title", "sentence_speaker"]).sum()

        return main_speaker_sentences_grouped

    def get_results_grouped_by_faction(self):
        if self.analysis_results is None:
            raise ValueError("Must analyse speeches before getting results")

        results_df_grouped = self.analysis_results[["main_speaker_faction", "total_duration", "duration_positive",
                                                    "duration_neutral", "duration_negative"]].groupby(["main_speaker_faction"]).sum()

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

        grouped_by_party = self.get_results_grouped_by_faction()
        grouped_by_party["keyword"] = self.keyword
        grouped_by_party.to_csv(
            "results/" + self.keyword + "_grouped_by_faction"+timestamp+".csv")

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

        try:
            analysis_results = {
                "total_duration": total_duration,
                "duration_positive": duration_positive,
                "duration_neutral": duration_neutral,
                "duration_negative": duration_negative,
                "agenda_item_title": metadata["agenda_item_title"],
                "main_speaker": metadata["main_speaker"],
                "main_speaker_party": metadata["main_speaker_party"],
                "main_speaker_faction": metadata["main_speaker_faction"]
            }
        except:
            print(metadata)
            raise ValueError("Invalid metadata")

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
