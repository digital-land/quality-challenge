from crawl4ai.deep_crawling.filters import ContentTypeFilter, URLPatternFilter
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

from data_quality_utils import Crawler


def test_crawler_initialization():
    crawler = Crawler()
    assert crawler is not None


def test_filter_initialisation():
    filters = [
        {"type": "ContentTypeFilter", "allowed_types": ["text/html"]},
        {"type": "URLPatternFilter", "patterns": ["*tests*"]},
    ]
    crawler = Crawler(filters=filters)

    assert len(crawler.filter_chain.filters) == 2
    assert isinstance(crawler.filter_chain.filters[0], ContentTypeFilter)
    assert isinstance(crawler.filter_chain.filters[1], URLPatternFilter)


def test_scorer_initialisation():
    keyword_scorer = {
        "keywords": ["conservation", "planning", "building", "heritage"],
        "weight": 0.8,
    }
    crawler = Crawler(keyword_scorer=keyword_scorer)

    assert isinstance(crawler.keyword_scorer, KeywordRelevanceScorer)
    assert crawler.keyword_scorer._keywords == keyword_scorer["keywords"]
