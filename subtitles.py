#!/usr/bin/env python3

import argparse
import json
import re

THRESHOLD = 900


def generate_subtitles(words, lang="fr-FR"):
    n = len(words)
    subtitles = []
    sentence = ""
    first_timestamp = 0
    line = 0
    for i, (timestamp, word) in enumerate(words):
        if not sentence:
            first_timestamp = timestamp

        # add word
        if sentence and not sentence.endswith("\n"):
            sentence += f" {word}"
        else:
            sentence += word

        # add a line return if necessary
        if word[-1] in [",", "?", "."] or len(sentence.split("\n")[-1]) >= 38:
            sentence += "\n"
            line += 1

        # retrieve next word's timestamp
        if i + 1 == n:
            next_timestamp = 0xffffffff
        else:
            next_timestamp, _ = words[i+1]

        # the duration is wrong since it doesn't take current word length into account
        duration = next_timestamp - timestamp

        if duration > THRESHOLD or line == 2:
            subtitles.append((first_timestamp, sentence))
            sentence = ""
            line = 0

    return subtitles


def generate_chat(words):
    words = " ".join([sentence for _, sentence in words])
    words = re.sub("\n", " ", words)
    words = re.sub(" +", " ", words)
    # fix french punctuation
    words = re.sub(r"([,\.])([\w])", r"\1 \2", words)
    words = re.sub(r"([\w])([;:?!])", r"\1 \2", words)
    words = re.sub(r"([\.?!])\s+", r"\1\n\n", words)
    print(words)


def ts_to_time(timestamp, separator="."):
    SECONDS_RATIO = 1000
    MINUTES_RATIO = SECONDS_RATIO * 60
    HOURS_RATIO = MINUTES_RATIO * 60
    hours = timestamp % HOURS_RATIO
    minutes = timestamp
    ms = timestamp % SECONDS_RATIO
    seconds = (timestamp // SECONDS_RATIO) % 60
    minutes = (timestamp // MINUTES_RATIO) % 60
    hours = timestamp // HOURS_RATIO
    return "%02d:%02d:%02d%c%03d" % (hours, minutes, seconds, separator, ms)


def srt(subtitles):
    n = len(subtitles)
    for i, (timestamp, sentence) in enumerate(subtitles):
        print(f"{i + 1}")
        if i + 1 == n:
            duration = 1000
        else:
            duration, _ = subtitles[i+1]
            duration -= timestamp + 500
        print(f"{ts_to_time(timestamp, ',')} --> {ts_to_time(timestamp + duration, ',')}")
        print(f"{sentence}\n")


def vtt(subtitles):
    print("WEBVTT\n")

    n = len(subtitles)
    for i, (timestamp, sentence) in enumerate(subtitles):
        print(f"{i + 1}")
        if i + 1 == n:
            duration = 1000
        else:
            duration, _ = subtitles[i+1]
            duration -= timestamp + 100
        print(f"{ts_to_time(timestamp)} --> {ts_to_time(timestamp + duration)}")
        print(f"{sentence}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--format", type=str, choices=["srt", "txt", "vtt"], default="vtt")
    parser.add_argument("file", type=str, help="JSON file")
    args = parser.parse_args()

    with open(args.file) as fp:
        data = fp.read()

    data = data.replace("(", "[")
    data = data.replace(")", "]")
    data = data.replace(",\n]", "\n]")

    words = json.loads(data)

    if args.format == "srt":
        subtitles = generate_subtitles(words)
        srt(subtitles)
    elif args.format == "vtt":
        subtitles = generate_subtitles(words)
        vtt(subtitles)
    else:
        generate_chat(words)
