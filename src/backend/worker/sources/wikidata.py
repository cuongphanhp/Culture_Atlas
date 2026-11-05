"""Wikidata SPARQL — thông tin nền quốc gia (thủ đô, ngôn ngữ chính thức, tiền tệ, láng giềng, dân số). CC0, không cần xác thực."""
from __future__ import annotations

from worker.core.models import CountryRecord, Provenance
from worker.sources.base import Source

ENDPOINT = "https://query.wikidata.org/sparql"
QUERY = """
SELECT ?iso2 ?country ?countryLabel ?iso3 ?num ?capitalLabel ?population
       (GROUP_CONCAT(DISTINCT ?langLabel; separator="|") AS ?langs)
       (GROUP_CONCAT(DISTINCT ?curLabel; separator="|") AS ?curs)
       (GROUP_CONCAT(DISTINCT ?nbIso; separator="|") AS ?neighbors)
WHERE {
  VALUES ?iso2 { %s }
  ?country wdt:P297 ?iso2 ; wdt:P31 wd:Q6256 .
  OPTIONAL { ?country wdt:P298 ?iso3 }
  OPTIONAL { ?country wdt:P299 ?num }
  OPTIONAL { ?country wdt:P36 ?capital }
  OPTIONAL { ?country wdt:P1082 ?population }
  OPTIONAL { ?country wdt:P37 ?lang . ?lang rdfs:label ?langLabel FILTER(LANG(?langLabel) = "en") }
  OPTIONAL { ?country wdt:P38 ?cur . ?cur rdfs:label ?curLabel FILTER(LANG(?curLabel) = "en") }
  OPTIONAL { ?country wdt:P47 ?nb . ?nb wdt:P297 ?nbIso ; wdt:P31 wd:Q6256 }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?iso2 ?country ?countryLabel ?iso3 ?num ?capitalLabel ?population
"""


def parse_bindings(rows: list[dict]) -> list[CountryRecord]:
    best: dict[str, dict] = {}
    for b in rows:
        iso = b["iso2"]["value"]
        pop = int(float(b["population"]["value"])) if "population" in b else 0
        if iso not in best or pop > best[iso]["_pop"]:  # nhiều giá trị dân số theo năm → lấy số lớn nhất (mới nhất)
            best[iso] = {**b, "_pop": pop}
    out = []
    for iso, b in sorted(best.items()):
        split = lambda k: sorted(x for x in b.get(k, {}).get("value", "").split("|") if x)
        out.append(CountryRecord(
            iso2=iso, name_en=b["countryLabel"]["value"], capital=b.get("capitalLabel", {}).get("value"),
            languages=split("langs"), currencies=split("curs"), neighbors=split("neighbors"),
            population=b["_pop"] or None, iso3=b.get("iso3", {}).get("value"), iso_numeric=b.get("num", {}).get("value"),
            provenance=Provenance("wikidata", b["country"]["value"], "CC0 1.0")))
    return out


class WikidataCountries(Source):
    name, title = "wikidata", "Wikidata — country facts (SPARQL)"
    access, auth, license, homepage = "api", "none", "CC0 1.0", "https://query.wikidata.org"

    def collect(self):
        values = " ".join(f'"{c}"' for c in self.ctx.countries)
        data = self.ctx.http.get_json(ENDPOINT, respect_robots=False, params={"query": QUERY % values, "format": "json"},
                                      headers={"Accept": "application/sparql-results+json"})
        self.raw.save("countries", data)
        yield from parse_bindings(data["results"]["bindings"])
