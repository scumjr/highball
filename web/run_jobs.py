#!/usr/bin/env python3

"""
Transcription pipeline, runs one job at a time.
"""

import logging
import os
import pathlib
import re
import subprocess
import sys

from collections import namedtuple

Job = namedtuple("Job", "output_ext input_ext function")

INPUT_EXTS = ["mp3", "mp4"]
OUTPUT_EXTS = ["json", "png", "srt", "txt", "wav"]


def run_job_convert_audio(media_path, wav):
    args = ["ffmpeg", "-loglevel", "error", "-i", media_path, "-ar", "44100", wav]
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


def run_job_thumbnail(media_path, png, position=5):
    args = ["ffmpeg", "-loglevel", "error",
            "-accurate_seek", "-ss", f"{position}"]
    if media_path.endswith(".mp3"):
        args += ["-f", "lavfi", "-i", "color=c=black"]
    args += ["-i", media_path, "-frames:v", "1", "-s", "128x80", png]
    subprocess.run(args)


def run_job(path, name):
    """
    Generate subtitles, transcript, thumbnail, etc. from an audio or video file.
    """

    logging.debug(f'running job "{name}"')

    extensions = INPUT_EXTS + OUTPUT_EXTS
    paths = dict([(ext, os.path.join(path, f"{name}.{ext}")) for ext in extensions])

    jobs = [
        Job("wav", "mp4", run_job_convert_audio),
        Job("json", "wav", run_job_transcript),
        Job("srt", "json", run_job_subtitles),
        Job("txt", "json", run_job_chat),
        Job("png", "mp4", run_job_thumbnail),
    ]

    for job in jobs:
        output_path = paths[job.output_ext]
        input_path = paths[job.input_ext]
        if not os.path.exists(output_path):
            if job.input_ext == "mp4" and not os.path.exists(paths["mp4"]):
                input_path = paths["mp3"]
            logging.debug(f'"{input_path}" => "{output_path}"')
            job.function(input_path, output_path)


def list_jobs(path):
    """
    List a directory to retrieve filenames matching input extensions.
    """

    extensions = [f".{ext}" for ext in INPUT_EXTS]
    files = os.listdir(path)
    files = [name for name in files if pathlib.PurePosixPath(name).suffix in extensions]
    names = list(set([pathlib.PurePosixPath(name).stem for name in files]))

    # Ensure filenames don't contain unexpected characters to prevent command
    # injection issues (ffmpeg options handling looks hazardous).
    names = [name for name in names if re.match("^[a-z][a-z0-9._ -]*$", name, re.IGNORECASE)]

    return names


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    script_dir = os.path.dirname(os.path.realpath(__file__))

    if len(sys.argv) == 2:
        path = os.path.abspath(sys.argv[1])
    else:
        path = os.path.abspath(os.path.join(script_dir, "../../audio"))

    os.chdir(script_dir)

    with open("job.pid", "w") as fp:
        fp.write(f"{os.getpid()}")

    jobs = list_jobs(path)
    logging.debug(f"jobs: {jobs}")
    for name in jobs:
        run_job(path, name)

    try:
        os.remove("job.pid")
    except FileNotFoundError:
        pass
