"""Danh sách nguồn — thứ tự chạy mặc định."""
from worker.sources.europeana import Europeana
from worker.sources.official_sites import OfficialTourismSites
from worker.sources.rest_countries import RestCountries
from worker.sources.scale import ScaleCulturalData
from worker.sources.smithsonian import SmithsonianOpenAccess
from worker.sources.unesco_datahub import UnescoIntangibleHeritage, UnescoWorldHeritage
from worker.sources.wikidata import WikidataCountries
from worker.sources.wikimedia_commons import WikimediaCommons
from worker.sources.wikipedia import Wikipedia

REGISTRY = {cls.name: cls for cls in (
    WikidataCountries, RestCountries, UnescoWorldHeritage, UnescoIntangibleHeritage, SmithsonianOpenAccess,
    Europeana, WikimediaCommons, Wikipedia, ScaleCulturalData, OfficialTourismSites,
)}
