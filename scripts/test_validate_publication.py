import unittest
from validate_publication import validate_publication


class PublicationContractTests(unittest.TestCase):
    def test_optional_and_existing_quote(self):
        validate_publication({}, 0)
        validate_publication({'newsletter': {'featuredQuoteIndex': 0}}, 1)

    def test_three_original_quotes(self):
        validate_publication({'newsletter': {'featuredQuoteIndices': [0, 2, 3]}}, 4)
        for indices in [[], [0, 0], [0, 1, 2, 3], [-1], [4], [True]]:
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                validate_publication({'newsletter': {'featuredQuoteIndices': indices}}, 4)

    def test_real_episode_url_shape(self):
        validate_publication({'podcast': {'title': '标题', 'url': 'https://www.xiaoyuzhoufm.com/episode/' + 'a' * 24, 'durationSeconds': 45, 'publishedAt': '2026-10-27'}}, 0)

    def test_invalid_podcast_values(self):
        for url in ['javascript:alert(1)', 'https://xiaoyuzhoufm.com.evil.test/episode/' + 'a' * 24,
                    'https://xiaoyuzhoufm.com/podcast/' + 'a' * 24,
                    'https://user@xiaoyuzhoufm.com/episode/' + 'a' * 24]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_publication({'podcast': {'title': '标题', 'url': url}}, 0)
        with self.assertRaises(ValueError):
            validate_publication({'podcast': {'title': '标题', 'url': 'https://xiaoyuzhoufm.com/episode/' + 'a' * 24, 'publishedAt': '2026-02-30'}}, 0)

    def test_invalid_quote_index_and_fields(self):
        for index in [-1, 1, True, 0.5]:
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_publication({'newsletter': {'featuredQuoteIndex': index}}, 1)
        with self.assertRaises(ValueError):
            validate_publication({'email': 'private@example.com'}, 0)


if __name__ == '__main__':
    unittest.main()
