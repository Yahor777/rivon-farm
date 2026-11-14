"""Second pass: read the candidate list (lib-sfx/sfx_candidates.json), open each Freesound page (CC0 filter was applied
in the search; the licence is re-checked on the page), keep title / duration / tags / description and download the HQ
preview. Commons PD/CC0 files with relevant titles are taken too. Output: <out>/<category>/<id>.mp3|ogg + sfx_report.json"""
import json, sys, re, time, html, urllib.request, subprocess
from pathlib import Path
UA = {"User-Agent": "Mozilla/5.0 (rivon-film-sfx; github.com/Yahor777/rivon-farm)"}
cand = json.loads(subprocess.check_output(["gh", "release", "download", "lib-sfx", "-p", "sfx_candidates.json", "-O", "-"]))
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True); K = 9; rep = {}


def get(url, binary=False):
    for i in range(5):
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            return d if binary else d.decode("utf-8", "replace")
        except Exception as e:
            if "429" in repr(e):
                time.sleep(20 * (i + 1)); continue
            if i == 4:
                raise
            time.sleep(3)
    raise RuntimeError("429 " + url)


for cat, rows in cand.items():
    rep[cat] = []; (out / cat).mkdir(exist_ok=True); seen = set(); n = 0
    for r in rows:
        if r.get("src") != "freesound" or "id" not in r or r["id"] in seen or n >= K:
            continue
        seen.add(r["id"])
        try:
            h = get(f"https://freesound.org/s/{r['id']}/"); time.sleep(1.2)
        except Exception as e:
            rep[cat].append({"id": r["id"], "error": repr(e)}); continue
        lic = "CC0" if re.search(r"creativecommons\.org/publicdomain/zero", h) else ("BY" if "licenses/by" in h else "?")
        title = html.unescape((re.search(r'<meta property="og:title" content="([^"]*)"', h) or [None, ""])[1])
        desc = html.unescape((re.search(r'<meta property="og:description" content="([^"]*)"', h) or [None, ""])[1])[:300]
        mp3 = (re.search(r'<meta property="og:audio" content="([^"]*)"', h) or re.search(r'data-mp3="([^"]+)"', h) or [None, ""])[1]
        dur = (re.search(r'data-duration="([\d.]+)"', h) or [None, ""])[1]
        tags = re.findall(r'/browse/tags/([^/"]+)/', h)[:12]
        e = {"id": r["id"], "title": title, "licence": lic, "duration": dur, "desc": desc, "tags": tags, "q": r.get("q"), "mp3": mp3}
        if lic == "CC0" and mp3:
            try:
                (out / cat / f"{r['id']}.mp3").write_bytes(get(mp3 if mp3.startswith("http") else "https:" + mp3, binary=True)); e["file"] = f"{cat}/{r['id']}.mp3"; n += 1
            except Exception as ex:
                e["error"] = repr(ex)
        rep[cat].append(e)
    for r in rows:                                               # Commons: only titles that are clearly field recordings
        t = (r.get("title") or "")
        if r.get("src") == "commons" and re.search(r"rain|thunder|wind|wave|sea|storm|bird|drop|wood|metal|door|knock|creak", t, re.I) \
                and not re.search(r"LL-Q|pronunciation|\bEn-|Nl-|Rm-|Komiku|Loyalty|Remarks|Čapek", t):
            try:
                ext = r["url"].rsplit(".", 1)[-1][:4]; fn = re.sub(r"[^A-Za-z0-9]+", "_", t)[:60] + "." + ext
                (out / cat / fn).write_bytes(get(r["url"], binary=True)); rep[cat].append({"src": "commons", "title": t, "licence": r.get("licence"), "file": f"{cat}/{fn}", "url": r["url"]})
            except Exception as ex:
                rep[cat].append({"src": "commons", "title": t, "error": repr(ex)})
json.dump(rep, open(out / "sfx_report.json", "w"), indent=1, ensure_ascii=False)
print({k: sum(1 for x in v if "file" in x) for k, v in rep.items()})
