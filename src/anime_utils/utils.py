from http.cookiejar import MozillaCookieJar
from http.cookies import SimpleCookie
from urllib.request import Request


class AioCookieJar(MozillaCookieJar):
    """MozillaCookieJar with aiohttp compatibility."""

    def filter_cookies(self, url):
        cookie = SimpleCookie()
        req = Request(url)
        self.add_cookie_header(req)
        cookie_header = req.get_header("Cookie")
        if cookie_header:
            cookie.load(cookie_header)
        return cookie

    def update_cookies(self, cookies, response_url=None):
        pass
