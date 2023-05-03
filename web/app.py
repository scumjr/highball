#!/usr/bin/env python3

import os
import pathlib
import re
import sys
from flask import Flask, Response, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

MEDIA_PATH = "../../audio/"

app = Flask(__name__)

# private stuff that shouldn't be published on GitHub
if os.path.exists("custom.py"):
    import builtins
    builtins.app = app
    import custom


def list_directory_(files):
    extensions = [".mp3", ".mp4", ".srt", ".txt"]
    files = [name for name in files if pathlib.PurePosixPath(name).suffix in extensions]
    names = list(set([pathlib.PurePosixPath(name).stem for name in files]))

    result = []
    for name in names:
        line = {}
        for ext in extensions:
            if f"{name}{ext}" in files:
                line[ext] = f"{name}{ext}"
        result.append(line)

    return result


def list_directory(path):
    files = os.listdir(path)
    result = list_directory_(files)
    result.sort(key=lambda line: min([os.stat(os.path.join(path, f)) for f in line.values()]), reverse=True)
    return result


def upload_file():
    if "file" not in request.files:
        return Response("Upload error: no file.")

    file = request.files["file"]
    if file.filename == "":
        return Response("Upload error: no selected file.")

    if "/" in file.filename or pathlib.PurePosixPath(file.filename).suffix not in [".mp3", ".mp4"]:
        return Response("Upload error: invalid file name.")

    filename = secure_filename(file.filename)
    dst = os.path.join(MEDIA_PATH, filename)
    if os.path.exists(dst):
        return Response("Upload error: file already exists.")

    file.save(dst)

    run_jobs()
    return Response("The file was uploaded successfully and the transcription job is being queued.")


def run_jobs():
    try:
        with open("job.pid") as fp:
            data = fp.read()
        pid = int(data)
        os.kill(pid, 0)
        running = True
    except OSError:
        running = False
    except:
        running = False

    if not running:
        if os.fork() == 0:
            os.execvp("./run_jobs.py", ["run_jobs.py"])
            sys.exit(1)

    return running


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return upload_file()
    else:
        lines = list_directory(MEDIA_PATH)
        jobs = run_jobs()
        return render_template("index.html", lines=lines, jobs=jobs)


def delete_files(filename):
    assert "/" not in filename

    # order is important (prevent run_jobs.py from detecting an incomplete job)
    extensions = [".mp3", ".mp4", ".wav", ".json", ".txt", ".srt"]

    root, _ = os.path.splitext(filename)
    files = [os.path.join(MEDIA_PATH, f"{root}{ext}") for ext in extensions]
    for filename in files:
        try:
            os.remove(filename)
        except FileNotFoundError:
            pass
    return ""


def strip_timestamps(filename, as_attachment):
    with open(os.path.join(MEDIA_PATH, filename)) as fp:
        data = fp.read()
    data = re.sub(r"\[.*\]\s+", "", data)
    headers = {}
    if as_attachment:
        headers["Content-Disposition"] = f"attachment; filename={filename}"
    return Response(data, mimetype="text/plain", headers=headers)


@app.route("/audio/<filename>", methods=["GET", "DELETE"])
def audio(filename):
    if request.method == "DELETE":
        return delete_files(filename)
    else:
        as_attachment = "download" in request.args
        if os.path.splitext(filename)[1] == ".txt" and "strip" in request.args:
            return strip_timestamps(filename, as_attachment)
        else:
            return send_from_directory(MEDIA_PATH, filename, as_attachment=as_attachment)


@app.route("/player/<filename>")
def player(filename):
    root, ext = os.path.splitext(filename)
    if ext in [".mp3", ".mp4"] and os.path.exists(os.path.join(MEDIA_PATH, filename)):
        filename = os.path.join("/audio", filename)
        subtitles = f"{os.path.splitext(filename)[0]}.srt"
        return render_template("player.html", mp3=filename, subtitles=subtitles)
    else:
        return ("File not found.", 404)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
