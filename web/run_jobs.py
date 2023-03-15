#!/usr/bin/env python3

"""
Transcription pipeline, runs one job at a time.

.mp4/.mp3 => .wav => .json => .srt, .txt
"""

import os
import pathlib
import subprocess
import sys


def list_directory(path):
    extensions = [".mp4", ".mp3", ".wav", ".json", ".srt"]
    files = os.listdir(path)
    files = [name for name in files if pathlib.PurePosixPath(name).suffix in extensions]
    names = list(set([pathlib.PurePosixPath(name).stem for name in files]))

    return names


def list_jobs(path):
    names = list_directory(path)
    return [name for name in names if not os.path.exists(os.path.join(path, f"{name}.srt"))]


def run_job_convert_audio(mp3, wav):
    args = ["ffmpeg", "-i", mp3, "-ar", "44100", wav]
    subprocess.run(args)


def run_job_transcript(wav, json):
    args = ["sox", wav, "-c", "1", "-ts16", "-"]
    with open(json, "wb") as fp:
        highball = subprocess.Popen(["./highball"], cwd="../src/", stdin=subprocess.PIPE, stdout=fp)
        sox = subprocess.Popen(args, stdout=highball.stdin)
        sox.wait()
        # Even if the sox process has terminated, the highball process continues
        # because stdin isn't closed.
        highball.stdin.close()
        highball.wait()


def run_job_subtitles(json, srt):
    args = ["../subtitles.py", "--format", "vtt", json]
    with open(srt, "wb") as fp:
        subprocess.run(args, stdout=fp)


def run_job_chat(json, txt):
    args = ["../subtitles.py", "--format", "txt", json]
    with open(txt, "wb") as fp:
        subprocess.run(args, stdout=fp)


def run_job(path, name):
    extensions = ["mp4", "mp3", "wav", "json", "srt", "txt"]
    paths = dict([(ext, os.path.join(path, f"{name}.{ext}")) for ext in extensions])

    if not os.path.exists(paths["srt"]):
        if not os.path.exists(paths["json"]):
            if not os.path.exists(paths["wav"]):
                if os.path.exists(paths["mp4"]):
                    run_job_convert_audio(paths["mp4"], paths["wav"])
                else:
                    run_job_convert_audio(paths["mp3"], paths["wav"])
            run_job_transcript(paths["wav"], paths["json"])
        run_job_subtitles(paths["json"], paths["srt"])
        run_job_chat(paths["json"], paths["txt"])


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))

    if len(sys.argv) == 2:
        path = sys.argv[1]
    else:
        path = os.path.abspath(os.path.join(script_dir, "../../audio"))

    with open("job.pid", "w") as fp:
        fp.write(f"{os.getpid()}")

    path = os.path.abspath(path)
    os.chdir(script_dir)
    jobs = list_jobs(path)
    for name in jobs:
        run_job(path, name)

    os.unlink("job.pid")
