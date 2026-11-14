"""Find real, free-licence recordings for the film sound. Sources with open APIs and licence metadata:
Wikimedia Commons (CC0 / public domain only) and, if reachable, Freesound's public search (CC0 filter).
Writes candidates (title, licence, duration, url) as JSON; downloads nothing copyrighted or attribution-bound."""
import json, sys, re, urllib.request, urllib.parse, html

QUERIES = {
    "sea_waves": ["sea waves beach", "ocean waves shore", "Baltic sea waves"],
    "wind_gust": ["wind gust", "strong wind trees", "wind howling"],
    "leaves_rustle": ["leaves rustling wind", "tree leaves wind"],
    "thunder": ["thunder", "thunder rumble", "thunderclap"],
    "rain_heavy": ["heavy rain", "rain downpour", "rainstorm"],
    "rain_roof": ["rain on glass roof", "rain on roof", "rain on window", "rain skylight"],
    "wood_on_metal": ["wood hits metal", "wooden beam drop", "wood plank drop", "timber thud", "wood knock"],
    "wood_creak": ["wood creak", "timber creak"],
    "metal_clank": ["metal clank", "steel clang", "metal bracket"],
    "screwdriver": ["cordless drill screw", "electric screwdriver", "impact driver", "screw driving wood"],
    "water_drop": ["water drop", "drop into water", "water drip plop"],
    "glass_set": ["glass clink", "glass pane", "wine glass ding"],
    "switch": ["light switch", "switch click"],
    "birds": ["birds singing after rain", "blackbird song", "birdsong garden"],
    "cloth_flap": ["cloth flapping wind", "fabric flap", "flag flapping"],
    "whoosh_low": ["sub bass drop", "low rumble", "bass boom"],
}
UA = {"User-Agent": "rivon-film-sfx/1.0 (github.com/Yahor777/rivon-farm)"}
out = {}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode("utf-8", "replace")


def commons(q):
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=25"
           "&gsrsearch=" + urllib.parse.quote(f"filetype:audio {q}") + "&prop=imageinfo&iiprop=url|extmetadata|size|mediatype")
    res = []
    try:
        d = json.loads(get(url))
    except Exception as e:
        return [{"error": repr(e)}]
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        lic = (m.get("LicenseShortName", {}) or {}).get("value", "")
        if not re.search(r"CC0|Public domain|PD", lic, re.I):
            continue
        res.append({"src": "commons", "title": p.get("title"), "licence": lic, "url": ii.get("url"), "bytes": ii.get("size"),
                    "desc": re.sub("<[^>]+>", "", (m.get("ImageDescription", {}) or {}).get("value", ""))[:200],
                    "artist": re.sub("<[^>]+>", "", (m.get("Artist", {}) or {}).get("value", ""))[:60]})
    return res


def freesound(q):
    url = "https://freesound.org/search/?f=" + urllib.parse.quote('license:"Creative Commons 0" duration:[1 TO 120]') + "&s=" + urllib.parse.quote("Rating (highest first)") + "&q=" + urllib.parse.quote(q)
    res = []
    try:
        h = get(url)
    except Exception as e:
        return [{"error": repr(e)}]
    for m in re.finditer(r'data-sound-id="(\d+)"[^>]*?data-mp3="([^"]+)"[^>]*?data-duration="([\d.]+)"[^>]*?data-title="([^"]*)"', h, re.S):
        res.append({"src": "freesound", "id": int(m.group(1)), "url": m.group(2), "duration": float(m.group(3)),
                    "title": html.unescape(m.group(4)), "licence": "CC0 (search filter)"})
    if not res:
        ids = re.findall(r'/people/([^/]+)/sounds/(\d+)/', h)
        res = [{"src": "freesound", "user": u, "id": int(i), "licence": "CC0 (search filter)", "note": "no player attrs parsed"} for u, i in dict.fromkeys(ids)][:20]
        if not res:
            res = [{"error": "no results parsed", "len": len(h), "head": h[:200]}]
    return res


for key, qs in QUERIES.items():
    out[key] = []
    for q in qs:
        out[key] += [dict(r, q=q) for r in commons(q)] + [dict(r, q=q) for r in freesound(q)]
json.dump(out, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
