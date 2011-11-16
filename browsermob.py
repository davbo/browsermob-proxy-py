import json, httplib, urllib


URL_ENCODED = {'Content-type': 'application/x-www-form-urlencoded'}

class BrowserMobProxyHub(object):
    """The api for creating BrowserMobProxies.

    This object represents the actual java executable which supports multiple
    proxies running on a single process.
    """

    def __init__(self, hostname='localhost', port='8080'):
        self.hostname = hostname
        self.port = port

    @property
    def url(self):
        return "%s:%s" % (self.hostname, self.port)

    def get_connection(self):
        return httplib.HTTPConnection(self.url)

    def get_proxy(self, capture_headers=False, capture_content=False, port=None):
        """Returns a BrowserMobProxy object which exposes the full REST API"""
        conn = self.get_connection()
        if port:
            params = urllib.urlencode({
                'port': port,
                })
            conn.request("POST", "/proxy", params, headers=URL_ENCODED)
        else:
            conn.request("POST", "/proxy")
        port = json.load(conn.getresponse())['port']
        return BrowserMobProxy(self, port, capture_headers, capture_content)

class BrowserMobProxy(object):
    """Python wrapper for the BrowserMob Proxy REST API

    Multiple Proxies can be running on a single ProxyHub, they simply open on
    separate ports. This class represents them as separate discrete proxies.
    """

    def __init__(self, hub, port, capture_headers=False, capture_content=False):
        self.hub = hub
        self.port = port
        self.capture_headers = capture_headers
        self.capture_content = capture_content
        self.page_count = 1

    def new_har(self, initialPageRef="Page 1"):
        """Creates a new HAR attached to the proxy and returns the HAR content if there 
        was a previous HAR. Supports the following parameters:
            initialPageRef - the string name of the first page ref that should be used
            in the HAR. Defaults to "Page 1".
            capture_headers - If True the HAR will contain request/response headers.
            capture_content - If True the HAR will contain some content from the page.
            NOTE: capture_content doesn't seem to be working...
        """
        self.page_count = 1
        params = urllib.urlencode({
            'initialPageRef': initialPageRef,
            'captureContent': self.capture_content,
            'captureHeaders': self.capture_headers,
            })
        conn = self.hub.get_connection()
        conn.request("PUT", "/proxy/%s/har" % self.port, params,
                headers=URL_ENCODED)
        res = conn.getresponse().read()
        if res: return json.loads(res) # This could return an old HAR
        return True

    def new_page(self, pageRef=None):
        """Starts a new page on the existing HAR. Supports the following parameters:
            pageRef - the string name of the first page ref that should be used 
            in the HAR. Defaults to "Page N" where N is the next page number.
        """
        self.page_count += 1
        if not pageRef:
            pageRef = "Page %s" % self.page_count
        params = urllib.urlencode({'pageRef': pageRef})
        conn = self.hub.get_connection()
        conn.request("PUT", "/proxy/%s/har/pageRef" % self.port, params,
                headers=URL_ENCODED)
        res = conn.getresponse()
        if res.status is 200:
            return True

    def set_headers(self, headers):
        params = urllib.urlencode(headers)
        conn = self.hub.get_connection()
        conn.request("PUT", "/proxy/%s/headers" % self.port, params,
                headers=URL_ENCODED)
        res = conn.getresponse()
        if res.status is 200:
            return True

    def _list(self, bw, regex, status):
        params = urllib.urlencode({'regex': regex, 'status': status})
        conn = self.hub.get_connection()
        conn.request("PUT", "/proxy/%s/%s" % (self.port, bw), params,
                headers=URL_ENCODED)
        res = conn.getresponse()
        if res.status is 200:
            return True

    def blacklist(self, regex, status):
        """Set a URL to blacklist. Takes the following parameters:
            regex - the blacklist regular expression
            status - the HTTP status code to return for URLs that are blacklisted
        """
        return self._list('blacklist', regex, status)

    def whitelist(self, regex, status):
        """Sets a list of URL patterns to whitelist. Takes the following parameters:
            regex - a comma separated list of regular expressions
            status - the HTTP status code to return for URLs that do not match the whitelist
        """
        return self._list('whitelist', regex, status)

    def limit_bandwidth(self, down=None, up=None, latency=None):
        """Limit the bandwidth through the proxy. Takes the following parameters:
            downstreamKbps - Sets the downstream kbps
            upstreamKbps - Sets the upstream kbps
            latency - Add the given latency to each HTTP request
        """
        if not down and not up and not latency: return False
        params = dict()
        if down: params['downstreamKbps'] = down
        if up: params['upstreamKbps'] = up
        if latency: params['latency'] = latency
        params = urllib.urlencode(params)
        conn = self.hub.get_connection()
        conn.request("PUT", "/proxy/%s/limit" % self.port, params,
                headers=URL_ENCODED)
        res = conn.getresponse()
        if res.status is 200:
            return True

    def get_har(self):
        """Returns the JSON/HAR content representing all the HTTP traffic passed through the proxy"""
        conn = self.hub.get_connection()
        conn.request("GET", "/proxy/%s/har" % self.port)
        return json.load(conn.getresponse())

    def close_proxy(self):
        """Shuts down the proxy and closes the port"""
        conn = self.hub.get_connection()
        conn.request("DELETE", "/proxy/%s" % self.port)

if __name__ == '__main__':
    bmp = BrowserMobProxyHub()
    proxy = bmp.get_proxy()
