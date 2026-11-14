"""Third pass: the previous run already read every Freesound page (title / licence / duration / tags are in
lib-sfx/sfx_report.json) but built the preview URLs wrongly. Download the CC0 previews straight from the CDN using that
report (no page requests), and the Commons PD files with proper extensions. Output: <out>/<category>/<id>.mp3 + sfx_report.json"""
import json, sys, re, time, urllib.request, subprocess
from pathlib import Path
UA = {"User-Agent": "Mozilla/5.0 (rivon-film-sfx; github.com/Yahor777/rivon-farm)"}
rep = json.loads(subprocess.check_output(["gh", "release", "download", "lib-sfx", "-p", "sfx_report.json", "-O", "-"]))
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True); K = 16


def get(url):
    for i in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except Exception as e:
            if i == 4:
                raise
            time.sleep(20 * (i + 1) if "429" in repr(e) else 3)


for cat, rows in rep.items():
    (out / cat).mkdir(exist_ok=True); n = 0; seen = set()
    for e in rows:
        e.pop("error", None); e.pop("file", None)
        try:
            if e.get("src") == "commons":
                if e["title"] in seen:
                    continue
                seen.add(e["title"])
                ext = e["url"].split("?")[0].rsplit(".", 1)[-1][:4]; fn = re.sub(r"[^A-Za-z0-9]+", "_", e["title"])[:50] + "." + ext
                (out / cat / fn).write_bytes(get(e["url"])); e["file"] = f"{cat}/{fn}"
            elif e.get("licence") == "CC0" and e.get("mp3") and n < K and float(e.get("duration") or 999) <= 240:
                url = "https://" + e["mp3"].split("https://")[-1].replace("-lq.mp3", "-hq.mp3")
                (out / cat / f"{e['id']}.mp3").write_bytes(get(url)); e["file"] = f"{cat}/{e['id']}.mp3"; e["mp3"] = url; n += 1
                time.sleep(0.3)
        except Exception as ex:
            e["error"] = repr(ex)
json.dump(rep, open(out / "sfx_report.json", "w"), indent=1, ensure_ascii=False)
print({k: sum(1 for x in v if "file" in x) for k, v in rep.items()})
