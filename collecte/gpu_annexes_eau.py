# -*- coding: utf-8 -*-
"""Pour chaque commune (code INSEE et point longitude,latitude), trouve le document d'urbanisme en vigueur (API Carto GPU),
liste ses fichiers (API du Géoportail de l'urbanisme) et télécharge ceux qui concernent l'eau potable (annexes sanitaires,
AEP, eau potable, desserte, schéma directeur). Écrit out/INDEX_GPU.csv. Usage : python3 gpu_annexes_eau.py "insee:lon,lat ..." """
import csv, hashlib, json, os, re, sys, urllib.parse, urllib.request
MOTS = re.compile(r"(?i)sanitaire|aep|eau[_ -]?potable|potable|desserte|schema[_ -]?directeur|alimentation[_ -]en[_ -]eau|reseau[_ -]d.?eau|eau")
EXCLU = re.compile(r"(?i)pluvial|assainissement|nappe|inondation|captage|eaux[_ -]us")
UA = {"User-Agent": "Mozilla/5.0 (OMONEAU verification)"}
def get(u, binaire=False):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180)
    d = r.read(); return d if binaire else json.loads(d)
os.makedirs("out", exist_ok=True)
w = csv.writer(open("out/INDEX_GPU.csv", "w", newline="", encoding="utf-8"), delimiter=";")
w.writerow(["insee", "partition", "document", "titre", "fichier", "octets", "sha256", "url", "statut"])
for item in sys.argv[1].split():
    insee, pt = item.split(":"); lon, lat = map(float, pt.split(","))
    try:
        g = urllib.parse.quote(json.dumps({"type": "Point", "coordinates": [lon, lat]}))
        F = get(f"https://apicarto.ign.fr/api/gpu/document?geom={g}")["features"]
        docs = [f["properties"] for f in F if f["properties"].get("du_type") in ("PLU", "PLUi", "PLUiH", "POS", "CC", "PSMV")] or [f["properties"] for f in F]
        if not docs:
            w.writerow([insee, "", "", "", "", "", "", "", "aucun document"]); continue
        d = docs[0]; did = d.get("gpu_doc_id") or d.get("id")
        files = get(f"https://www.geoportail-urbanisme.gouv.fr/api/document/{did}/files")
        noms = [x if isinstance(x, str) else (x.get("name") or x.get("title") or "") for x in files]
        gard = [n for n in noms if n.lower().endswith((".pdf", ".zip")) and MOTS.search(n) and not (EXCLU.search(n) and not re.search(r"(?i)sanitaire|aep|potable", n))]
        if not gard:
            w.writerow([insee, d.get("partition"), did, d.get("grid_title"), "", "", "", "", f"aucun fichier eau parmi {len(noms)}"])
        for n in gard:
            u = f"https://www.geoportail-urbanisme.gouv.fr/api/document/{did}/files/{urllib.parse.quote(n)}"
            try:
                b = get(u, True); nom = f"{insee}__{n}"[:200]
                open("out/" + nom, "wb").write(b)
                w.writerow([insee, d.get("partition"), did, d.get("grid_title"), nom, len(b), hashlib.sha256(b).hexdigest(), u, "ok"])
            except Exception as e:
                w.writerow([insee, d.get("partition"), did, d.get("grid_title"), n, "", "", u, f"échec {e}"])
    except Exception as e:
        w.writerow([insee, "", "", "", "", "", "", "", f"échec {e}"])
