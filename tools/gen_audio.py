"""Génère un fichier audio par article avec Kokoro-82M (kokoro-onnx, voix française ff_siwis).

Usage (depuis la racine du projet) :
    tools/.venv/Scripts/python.exe tools/gen_audio.py              # tous les articles manquants
    tools/.venv/Scripts/python.exe tools/gen_audio.py --only ID    # un article
    tools/.venv/Scripts/python.exe tools/gen_audio.py --limit 3    # les 3 premiers manquants
    tools/.venv/Scripts/python.exe tools/gen_audio.py --force      # régénère même si le fichier existe

Sortie : app/audio/<id>.mp3 et app/audio/index.json (id -> durée en secondes, taille).
Le script reprend où il s'est arrêté : un fichier déjà généré est ignoré.
Les corrections de prononciation vont dans tools/lexique.json ({"texte écrit": "texte lu"}).
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "app" / "data" / "articles.json"
OUT = ROOT / "app" / "audio"
MODEL = ROOT / "tools" / "models" / "kokoro-v1.0.onnx"
VOICES = ROOT / "tools" / "models" / "voices-v1.0.bin"
LEXIQUE = ROOT / "tools" / "lexique.json"
VOICE, LANG, SPEED = "ff_siwis", "fr-fr", 0.95
SR = 24000
BITRATE = "64k"

ORD = {1: "premier", 2: "deuxième", 3: "troisième", 4: "quatrième", 5: "cinquième", 6: "sixième",
       7: "septième", 8: "huitième", 9: "neuvième", 10: "dixième", 11: "onzième", 12: "douzième",
       13: "treizième", 14: "quatorzième", 15: "quinzième", 16: "seizième", 17: "dix-septième",
       18: "dix-huitième", 19: "dix-neuvième", 20: "vingtième", 21: "vingt et unième"}


def roman(s):
    v = {"I": 1, "V": 5, "X": 10, "L": 50}
    tot = 0
    for i, c in enumerate(s):
        n = v[c]
        tot += -n if i + 1 < len(s) and v[s[i + 1]] > n else n
    return tot


def ordinal(n, first_masc=False):
    if n == 1:
        return "premier" if first_masc else "premier"
    return ORD.get(n, f"{n}e")


def normalise(t, lexique):
    t = t.replace("’", "'").replace(" ", " ").replace(" ", " ")
    t = re.sub(r"\bav\. J\.-C\.", "avant Jésus-Christ", t)
    t = re.sub(r"\bapr\. J\.-C\.", "après Jésus-Christ", t)
    t = re.sub(r"\bJ\.-C\.", "Jésus-Christ", t)
    t = re.sub(r"(?<!\d)(\d{1,3}) (\d{3})(?!\d)", r"\1\2", t)  # 1 400 -> 1400
    t = re.sub(r"(\d+)\s?%", r"\1 pour cent", t)
    t = re.sub(r"\b([IVXL]+)(?:er|e|ème|è)\b",
               lambda m: ordinal(roman(m.group(1))) if roman(m.group(1)) <= 21 else m.group(0), t)
    t = re.sub(r"\b1er\b", "premier", t)
    t = re.sub(r"\b(\d+)(?:e|ème)\b", lambda m: ordinal(int(m.group(1))), t)
    for a, b in lexique.items():
        t = t.replace(a, b)
    return t


def segments(a, lexique):
    """(texte, pause_après_en_secondes)"""
    out = [(a["titre"] + ".", 0.9)]
    for p in a["paragraphes"]:
        out.append((p, 0.55))
    if a.get("anecdote"):
        out[-1] = (out[-1][0], 1.0)
        out.append(("L'anecdote.", 0.5))
        out.append((a["anecdote"], 0.0))
    return [(normalise(t, lexique), p) for t, p in out]


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    found = sorted(base.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"))
    if found:
        return str(found[0])
    sys.exit("ffmpeg introuvable : winget install Gyan.FFmpeg")


def encode_mp3(samples, path):
    tmp = path.with_suffix(".wav")
    sf.write(tmp, samples, SR, subtype="PCM_16")
    subprocess.run([find_ffmpeg(), "-y", "-loglevel", "error", "-i", str(tmp), "-ac", "1", "-codec:a", "libmp3lame",
                    "-b:a", BITRATE, "-metadata", "comment=Kokoro-82M ff_siwis", str(path)], check=True)
    tmp.unlink()


def reindex():
    """Reconstruit index.json d’après les mp3 présents (durée via ffprobe)."""
    probe = str(Path(find_ffmpeg()).with_name("ffprobe.exe")) if os.name == "nt" else "ffprobe"
    index = {}
    for f in sorted(OUT.glob("*.mp3")):
        r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                           capture_output=True, text=True, check=True)
        index[f.stem] = {"s": round(float(r.stdout.strip()), 1), "kb": round(f.stat().st_size / 1024)}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--reindex", action="store_true", help="reconstruit index.json et s’arrête")
    args = ap.parse_args()
    if args.reindex:
        print(len(reindex()), "fichiers indexés")
        return

    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    lexique = json.loads(LEXIQUE.read_text(encoding="utf-8")) if LEXIQUE.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    index_path = OUT / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}

    todo = [a for a in articles if (not args.only or a["id"] == args.only)
            and (args.force or args.only or not (OUT / f"{a['id']}.mp3").exists())]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} article(s) à générer", flush=True)

    kokoro = Kokoro(str(MODEL), str(VOICES))
    t_start = time.time()
    audio_total = 0.0
    for n, a in enumerate(todo, 1):
        t0 = time.time()
        chunks = []
        for text, pause in segments(a, lexique):
            samples, sr = kokoro.create(text, voice=VOICE, speed=SPEED, lang=LANG)
            assert sr == SR
            chunks.append(samples)
            if pause:
                chunks.append(np.zeros(int(SR * pause), dtype=np.float32))
        audio = np.concatenate(chunks)
        path = OUT / f"{a['id']}.mp3"
        encode_mp3(audio, path)
        dur = len(audio) / SR
        audio_total += dur
        index[a["id"]] = {"s": round(dur, 1), "kb": round(path.stat().st_size / 1024)}
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")
        el = time.time() - t0
        print(f"[{n}/{len(todo)}] {a['id']}  {dur:5.0f}s audio  {el:4.0f}s calcul  {index[a['id']]['kb']} Ko", flush=True)
    if todo:
        reindex()
        print(f"Terminé : {audio_total/60:.1f} min d'audio en {(time.time()-t_start)/60:.1f} min", flush=True)


if __name__ == "__main__":
    sys.exit(main())
