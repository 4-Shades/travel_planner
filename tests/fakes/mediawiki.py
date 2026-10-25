"""FakeMediaWiki: a respx route standing in for the Wikivoyage API (TDD plan §2.3)."""

import httpx

API_URL = "https://en.wikivoyage.org/w/api.php"


def sentences(topic, count, words=14):
    """Plain sentences of about words + 1 tokens each, numbered so that every passage is distinct."""
    filler = " ".join(f"word{n}" for n in range(words - 3))
    return " ".join(f"{topic} fact {n} {filler}." for n in range(count))


def article(title, sections=("Understand", "Get in", "Get around", "See", "Do", "Eat", "Drink", "Sleep", "Stay safe"), revid=1000):
    """An article with a lead paragraph and about 600 tokens in each section."""
    return {"title": title, "revid": revid, "sections": {s: sentences(f"{title} {s}", 40) for s in sections}}


class FakeMediaWiki:
    """Answers action=query requests for the articles it holds, the way Wikivoyage does."""

    def __init__(self, respx_mock, articles):
        self.articles = {a["title"]: a for a in articles}
        self.route = respx_mock.get(API_URL)
        self.route.mock(side_effect=self._answer)

    def _answer(self, request):
        title = request.url.params["titles"]
        article = self.articles.get(title)
        if article is None:
            page = {"ns": 0, "title": title, "missing": True}
        else:
            extract = f"{title} is a city.\n\n" + "".join(
                f"\n\n== {section} ==\n{text}\n\n=== A subsection ===\nMore about {section}."
                for section, text in article["sections"].items()
            )
            url = f"https://en.wikivoyage.org/wiki/{title.replace(' ', '_')}"
            page = {
                "pageid": 1,
                "ns": 0,
                "title": title,
                "extract": extract,
                "revisions": [{"revid": article["revid"], "parentid": article["revid"] - 1}],
                "lastrevid": article["revid"],
                "fullurl": url,
                "canonicalurl": url,
            }
        return httpx.Response(200, json={"batchcomplete": True, "query": {"pages": [page]}})

    def set_revision(self, title, revid):
        self.articles[title]["revid"] = revid

    @property
    def titles_requested(self):
        return [call.request.url.params["titles"] for call in self.route.calls]

    @property
    def user_agents(self):
        return [call.request.headers.get("User-Agent", "") for call in self.route.calls]

    @property
    def requests(self):
        return [call.request for call in self.route.calls]
