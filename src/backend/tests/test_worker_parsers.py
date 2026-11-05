"""Kiểm thử parser và lớp lõi của worker — không gọi mạng."""
import time

from worker.core.http import RateLimiter, RobotsCache
from worker.pipeline.classify import guess_category
from worker.sources.europeana import parse_item
from worker.sources.official_sites import extract_sections, parse_sitemap
from worker.sources.rest_countries import parse_country
from worker.sources.smithsonian import parse_row
from worker.sources.unesco_datahub import parse_ich, parse_whc
from worker.sources.wikidata import parse_bindings
from worker.sources.wikipedia import parse_sections


def test_parse_whc_filters_country_and_reads_fields():
    row = {"id_no": "688", "name_en": "Historic Monuments of Ancient Kyoto", "iso_codes": "['JP']", "date_inscribed": "1994",
           "category": "Cultural", "criteria_txt": "(ii)(iv)", "danger": "False", "geo_point_2d": "{'lon': 135.7, 'lat': 35.0}",
           "short_description_en": "Built in A.D. 794 …"}
    rec = parse_whc(row, {"JP"})
    assert rec.unesco_id == "WHC-688" and rec.inscribed_year == 1994 and rec.lat == 35.0
    assert rec.provenance.license == "CC BY-SA 4.0"
    assert parse_whc(row, {"VN"}) is None


def test_parse_ich_multinational():
    row = {"ich_public_ref": "437", "title_en": "Gastronomic meal of the French", "countries": "['FR']", "inscription_year": "2010",
           "type_of_element_en": "Representative List", "http_url_en": "https://ich.unesco.org/en/RL/00437"}
    rec = parse_ich(row, {"FR", "JP"})
    assert rec.type == "intangible" and rec.inscribed_year == 2010 and rec.countries == ["FR"]


def test_wikipedia_sections_strip_references_and_skip_see_also():
    html = """<div class="mw-parser-output"><p>Intro text about bowing in Japan. """ + "x " * 120 + """<sup class="reference">[1]</sup></p>
      <h2>Gift giving</h2><p>Gifts are presented with both hands. """ + "y " * 120 + """</p>
      <h2>See also</h2><ul><li>Something unrelated """ + "z " * 120 + """</li></ul></div>"""
    secs = dict(parse_sections(html))
    assert "Gift giving" in secs and "See also" not in secs
    assert "[1]" not in secs["Introduction"]


def test_official_site_extract_skips_unrendered_templates():
    html = """<html><body><nav>menu</nav><main><h1>Etiquette in Japan</h1>
      <h2>${v.title}</h2><p>${v.body}</p>
      <h2>Bowing</h2><p>Bowing is a common way to greet people and to say thank you in Japan.</p></main></body></html>"""
    title, sections = extract_sections(html)
    assert title == "Etiquette in Japan"
    assert [h for h, _ in sections] == ["Bowing"]


def test_sitemap_index_and_urlset():
    idx = '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://a/s1.xml</loc></sitemap></sitemapindex>'
    urls, children = parse_sitemap(idx)
    assert urls == [] and children == ["https://a/s1.xml"]
    us = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://a/en/tips/</loc></url></urlset>'
    assert parse_sitemap(us) == (["https://a/en/tips/"], [])


def test_smithsonian_keeps_only_cc0_media():
    row = {"title": "Kimono", "content": {"descriptiveNonRepeating": {"data_source": "Cooper Hewitt", "record_link": "https://x/1",
           "online_media": {"media": [{"usage": {"access": "CC0"}, "thumbnail": "https://ids.si.edu/ids/deliveryService?id=1"}]}}}}
    assert parse_row(row, "JP").license == "CC0"
    row["content"]["descriptiveNonRepeating"]["online_media"]["media"][0]["usage"]["access"] = "Usage conditions apply"
    assert parse_row(row, "JP") is None


def test_europeana_rejects_closed_rights():
    it = {"title": ["Print"], "guid": "https://www.europeana.eu/item/1?utm=x", "dataProvider": ["Museum"],
          "rights": ["http://creativecommons.org/licenses/by-sa/4.0/"], "edmPreview": ["https://thumb"]}
    rec = parse_item(it, "JP")
    assert rec.url == "https://www.europeana.eu/item/1"
    it["rights"] = ["http://rightsstatements.org/vocab/InC/1.0/"]
    assert parse_item(it, "JP") is None


def test_rest_countries_tolerates_v3_shape():
    rec = parse_country({"cca2": "jp", "name": {"common": "Japan"}, "capital": ["Tokyo"], "languages": {"jpn": "Japanese"},
                         "currencies": {"JPY": {"name": "Japanese yen"}}, "borders": []})
    assert rec.iso2 == "JP" and rec.capital == "Tokyo" and rec.currencies == ["Japanese yen"]


def test_wikidata_picks_largest_population():
    b = lambda pop: {"iso2": {"value": "VN"}, "country": {"value": "http://www.wikidata.org/entity/Q881"},
                     "countryLabel": {"value": "Vietnam"}, "population": {"value": pop}, "langs": {"value": "Vietnamese"}}
    recs = parse_bindings([b("90000000"), b("100300000")])
    assert len(recs) == 1 and recs[0].population == 100300000


def test_robots_cache_blocks_disallowed_paths():
    class Resp:
        status_code, text = 200, "User-agent: *\nDisallow: /private/\n"

    class Sess:
        def get(self, *a, **k):
            return Resp()

    rc = RobotsCache(Sess(), "CultureAtlasBot/0.1", 5)
    assert rc.allowed("https://example.org/en/tips/")
    assert not rc.allowed("https://example.org/private/x")


def test_rate_limiter_spaces_requests():
    rl = RateLimiter(0.2)
    t0 = time.monotonic()
    rl.wait("a.org"); rl.wait("a.org"); rl.wait("b.org")
    assert 0.18 <= time.monotonic() - t0 < 0.5


def test_category_guess():
    assert guess_category("Gift giving", "Gifts are wrapped and given with both hands") == "gift_giving"
    assert guess_category("Weather", "It rains in June") is None


def test_category_heading_outweighs_body():
    body = "Japanese is the national language. Children present essays; festivals are mentioned once."
    assert guess_category("Language", body) is None
    assert guess_category("Chopsticks", "Rules for using chopsticks at a meal") == "food_dining"


def test_redact_hides_keys_in_errors():
    from worker.core.storage import redact
    msg = "Max retries exceeded with url: /search?q=Japan&api_key=SECRET123&rows=100 and wskey=abc"
    out = redact(msg)
    assert "SECRET123" not in out and "abc" not in out and "api_key=***" in out


def test_record_writer_keeps_other_countries(tmp_path):
    from worker.core.models import DocumentRecord
    from worker.core.storage import RecordWriter
    w = RecordWriter(tmp_path, "src", countries={"JP", "VN"})
    w.write(DocumentRecord("JP", "t", "a", "x")); w.write(DocumentRecord("VN", "t", "a", "y")); w.close()
    w = RecordWriter(tmp_path, "src", countries={"JP"})
    w.write(DocumentRecord("JP", "t", "b", "z")); w.close()
    lines = (tmp_path / "normalized" / "src.jsonl").read_text().splitlines()
    assert len(lines) == 2 and any('"VN"' in l for l in lines) and any('"b"' in l for l in lines)


def test_raw_store_masks_configured_secrets(tmp_path):
    from worker.core.storage import RawStore
    rs = RawStore(tmp_path, "src", "run", secrets=("mysecretkey",))
    p = rs.save("x", {"guid": "https://e.eu/item/1?utm_campaign=mysecretkey"})
    assert "mysecretkey" not in p.read_text()
