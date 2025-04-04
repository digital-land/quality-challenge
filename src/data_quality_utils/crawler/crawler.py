from typing import Optional

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.filters import (
    ContentRelevanceFilter,
    ContentTypeFilter,
    FilterChain,
    SEOFilter,
    URLFilter,
    URLPatternFilter,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer


class Crawler:
    """
    A class-based implementation of an asynchronous web crawler
    using Crawl4AI.

    :param max_depth: Maximum depth for crawling.
    :param include_external: Whether to include external links.
    :param keyword_scorer: Dictionary with 'keywords' (list) and
        'weight' (float).
    :param filters: List of filter configurations or filter instances.
    :param cache_enabled: Whether caching is enabled.
    """

    def __init__(
        self,
        max_depth: int = 6,
        include_external: bool = False,
        keyword_scorer: Optional[dict] = None,
        filters: Optional[list[dict | URLFilter]] = None,
        cache_enabled: bool = False,
    ):
        self.max_depth = max_depth
        self.include_external = include_external
        self.keyword_scorer = self._initialize_scorer(keyword_scorer)
        self.filter_chain = self._initialize_filters(filters)
        self.cache_enabled = cache_enabled

    def _initialize_filters(self, filters) -> FilterChain:
        """Converts filter dictionaries into filter objects."""
        filter_list = []
        if filters:
            for f in filters:
                if isinstance(f, dict):
                    filter_type = f.get("type")
                    if filter_type == "SEOFilter":
                        filter_list.append(
                            SEOFilter(
                                threshold=f.get("threshold", 0.6),
                                keywords=f.get("keywords", []),
                            )
                        )
                    elif filter_type == "ContentRelevanceFilter":
                        filter_list.append(
                            ContentRelevanceFilter(
                                query=f.get("query", ""),
                                threshold=f.get("threshold", 0.2),
                            )
                        )
                    elif filter_type == "ContentTypeFilter":
                        filter_list.append(
                            ContentTypeFilter(
                                allowed_types=f.get("allowed_types", ["text/html"])
                            )
                        )
                    elif filter_type == "URLPatternFilter":
                        filter_list.append(
                            URLPatternFilter(patterns=f.get("patterns", []))
                        )
                elif isinstance(f, object):
                    filter_list.append(f)

        return FilterChain(filter_list)

    def _initialize_scorer(self, keyword_scorer) -> Optional[KeywordRelevanceScorer]:
        """Creates a keyword relevance scorer if keywords are provided."""
        if keyword_scorer:
            return KeywordRelevanceScorer(
                keywords=keyword_scorer.get("keywords", []),
                weight=keyword_scorer.get("weight", 1.0),
            )

    async def deep_crawl(self, url: str) -> list[tuple[str, str]]:
        """
        Performs a deep crawl on the given URL.

        :param url: The starting URL.

        :return: A list of tuples of (url, markdown)
        """
        # Create crawler configuration
        config = CrawlerRunConfig(
            deep_crawl_strategy=BestFirstCrawlingStrategy(
                max_depth=self.max_depth,
                include_external=self.include_external,
                url_scorer=self.keyword_scorer,
                filter_chain=self.filter_chain,
            ),
            scraping_strategy=LXMLWebScrapingStrategy(),
            cache_mode=CacheMode.ENABLED if self.cache_enabled else CacheMode.BYPASS,
            verbose=False,
        )

        crawl_data = []

        # Run the crawler
        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun(url, config=config)
            print(f"Crawled {len(results)} pages in total")

            for result in results:
                if result.success:
                    crawl_data.append((result.url, result.markdown.raw_markdown))

        return crawl_data
