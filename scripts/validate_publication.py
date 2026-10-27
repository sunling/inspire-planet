"""Validate the optional website/newsletter publication contract."""
from datetime import date
import re
from urllib.parse import urlsplit


def validate_publication(value, card_count):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    require(isinstance(value, dict), 'expected publication object')
    require(set(value) <= {'podcast', 'newsletter'}, 'unknown publication fields')
    if 'podcast' in value:
        podcast = value['podcast']
        require(isinstance(podcast, dict), 'podcast must be an object')
        require(set(podcast) <= {'url', 'title', 'durationSeconds', 'publishedAt'}, 'unknown podcast fields')
        require(text(podcast.get('title')), 'podcast title is required')
        raw_url = podcast.get('url')
        require(text(raw_url) and not re.search(r'[\s\x00-\x1f]', raw_url), 'podcast URL is required and cannot contain whitespace')
        url = urlsplit(raw_url)
        require(url.scheme == 'https' and url.hostname in {'xiaoyuzhoufm.com', 'www.xiaoyuzhoufm.com'}
                and not url.username and not url.password and url.port in (None, 443)
                and bool(re.fullmatch(r'/episode/[a-f0-9]{24}/?', url.path)), 'invalid Xiaoyuzhou episode URL')
        if 'durationSeconds' in podcast:
            duration = podcast['durationSeconds']
            require(type(duration) is int and duration > 0, 'durationSeconds must be a positive integer')
        if 'publishedAt' in podcast:
            published = podcast['publishedAt']
            require(isinstance(published, str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', published)), 'publishedAt must be YYYY-MM-DD')
            date.fromisoformat(published)
    if 'newsletter' in value:
        newsletter = value['newsletter']
        require(isinstance(newsletter, dict), 'newsletter must be an object')
        require(set(newsletter) <= {'intro', 'featuredQuoteIndex', 'featuredQuoteIndices'}, 'unknown newsletter fields')
        if 'intro' in newsletter:
            require(text(newsletter['intro']) and len(newsletter['intro']) <= 1000, 'intro must be nonempty and at most 1000 characters')
        if 'featuredQuoteIndex' in newsletter:
            index = newsletter['featuredQuoteIndex']
            require(type(index) is int and 0 <= index < card_count, 'featuredQuoteIndex must refer to an existing quote card')

        if 'featuredQuoteIndices' in newsletter:
            indices = newsletter['featuredQuoteIndices']
            require(isinstance(indices, list) and 1 <= len(indices) <= 3, 'select 1-3 quote indices')
            require(all(type(index) is int and 0 <= index < card_count for index in indices), 'featuredQuoteIndices must refer to existing quote cards')
            require(len(set(indices)) == len(indices) and 'featuredQuoteIndex' not in newsletter, 'indices must be unique; do not combine old and new fields')
