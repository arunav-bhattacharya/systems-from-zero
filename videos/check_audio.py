"""Listen to a finished video the way a learner would: transcribe its narration with Whisper and compare it
with the script (the captions). Mispronounced words show up as differences.

  .venv/bin/python check_audio.py <slug> [<slug> ...]

Prints loudness, the word match rate, and every phrase Whisper heard differently. A match rate above about
95% with differences only in punctuation-like spots (numbers, "e.g.") means the narration is clear.
"""
import difflib, re, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
WEB = HERE.parent / "web" / "video"
_model = None


NUM = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                       "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def words(t):
    """Lower-case words with digits and number words made the same, and apostrophes dropped, so only
    real differences in what was said remain."""
    t = t.lower().replace("€", " euro ").replace("'", "").replace("\u2019", "")
    return [NUM.get(w, w) for w in re.findall(r"[a-z0-9]+", t)]


def script(slug):
    lines = (WEB / f"{slug}.vtt").read_text().splitlines()
    return " ".join(l for l in lines if l and "-->" not in l and not l.isdigit() and l != "WEBVTT")


def heard(slug):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base.en", device="cpu", compute_type="int8")
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WEB / f"{slug}.mp4"), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = _model.transcribe(np.frombuffer(raw, np.float32), beam_size=5, language="en")
    return " ".join(s.text for s in segs)


def loudness(slug):
    out = subprocess.run(["ffmpeg", "-nostats", "-i", str(WEB / f"{slug}.mp4"), "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", out)
    return float(i.group(1)) if i else None


for slug in sys.argv[1:]:
    a, b = words(script(slug)), words(heard(slug))
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    match = sum(x.size for x in sm.get_matching_blocks()) / max(1, len(a))
    print(f"{slug}: loudness {loudness(slug)} LUFS, {len(a)} script words, match {match:.1%}")
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            print(f"   script: {' '.join(a[i1:i2]) or '-':40s} heard: {' '.join(b[j1:j2]) or '-'}")
