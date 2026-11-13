"""Fetch CC0 assets on a CI runner. Usage: fetch_assets.py request.json outdir"""
import json, os, sys, urllib.request, urllib.parse

UA = {"User-Agent": "rivon-farm-asset-fetch/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def save(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = get(url)
    with open(path, "wb") as f:
        f.write(data)
    print(f"  {len(data)/1e6:7.1f} MB  {path}")


def polyhaven(item, out):
    aid, res, fmt = item["id"], item.get("res", "4k"), item.get("fmt", "blend")
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    if fmt not in files:  # textures may lack .blend; fall back to gltf, then raw maps
        fmt = "gltf" if "gltf" in files else None
    base = os.path.join(out, "polyhaven", aid)
    if fmt:
        node = files[fmt].get(res) or files[fmt][sorted(files[fmt])[-1]]
        node = node[fmt]
        save(node["url"], os.path.join(base, os.path.basename(node["url"])))
        for rel, inc in node.get("include", {}).items():
            save(inc["url"], os.path.join(base, rel))
    else:
        for mapname, byres in files.items():
            if mapname in ("blend", "gltf", "fbx", "usd", "mtlx", "tonemapped", "colorchart", "backplates"):
                continue
            node = byres.get(res) or byres[sorted(byres)[-1]]
            ext = "exr" if "exr" in node else ("png" if "png" in node else "jpg")
            save(node[ext]["url"], os.path.join(base, f"{aid}_{mapname}_{res}.{ext}"))


def ambientcg(item, out):
    aid, res = item["id"], item.get("res", "4K")
    meta = json.loads(get(f"https://ambientcg.com/api/v2/full_json?id={aid}&include=downloadData"))
    dls = meta["foundAssets"][0]["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    pick = [d for d in dls if d["attribute"].startswith(res) and "PNG" in d["attribute"]] or \
           [d for d in dls if d["attribute"].startswith(res)] or dls
    import zipfile, io
    z = zipfile.ZipFile(io.BytesIO(get(pick[0]["fullDownloadPath"])))
    z.extractall(os.path.join(out, "ambientcg", aid))
    print(f"  ambientcg {aid} {pick[0]['attribute']}: {z.namelist()}")


def main():
    req = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if req.get("catalog"):
        cat = json.loads(get("https://api.polyhaven.com/assets?t=all"))
        slim = {k: {"type": v.get("type"), "name": v.get("name"), "categories": v.get("categories"),
                    "tags": v.get("tags"), "dims": v.get("dimensions"), "polycount": v.get("polycount"),
                    "dl": v.get("download_count")} for k, v in cat.items()}
        json.dump(slim, open(os.path.join(out, "polyhaven_catalog.json"), "w"), indent=0)
        acg, offset = [], 0
        while True:
            page = json.loads(get(f"https://ambientcg.com/api/v2/full_json?limit=250&offset={offset}&type=Material"))
            acg += [{"id": a["assetId"], "tags": a.get("tags"), "cat": a.get("displayCategory")} for a in page["foundAssets"]]
            if len(page["foundAssets"]) < 250:
                break
            offset += 250
        json.dump(acg, open(os.path.join(out, "ambientcg_catalog.json"), "w"), indent=0)
        print("polyhaven", len(slim), "ambientcg", len(acg))
    errors = []
    for it in req.get("polyhaven", []):
        try:
            polyhaven(it, out)
        except Exception as e:
            errors.append(f"polyhaven {it}: {e}")
    for it in req.get("ambientcg", []):
        try:
            ambientcg(it, out)
        except Exception as e:
            errors.append(f"ambientcg {it}: {e}")
    json.dump(errors, open(os.path.join(out, "errors.json"), "w"), indent=1)
    print("errors:", errors)


main()
