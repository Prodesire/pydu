import os
import shutil
import tempfile
from pydu.compat import PY2, string_types
from pydu.string import safeunicode

if PY2:
    import urllib as ulib
    import urlparse
else:
    import urllib.request as ulib
    import urllib.parse as urlparse


class FileName(object):
    @staticmethod
    def from_url(url):
        """
        Detected filename as unicode or None
        """
        filename = os.path.basename(urlparse.urlparse(url).path)
        if len(filename.strip(' \n\t.')) == 0:
            return None
        return safeunicode(filename)

    # http://greenbytes.de/tech/tc2231/
    @staticmethod
    def from_headers(headers):
        """
        Detect filename from Content-Disposition headers if present.

        headers: as dict, list or string
        """
        if not headers:
            return None

        if isinstance(headers, string_types):
            headers = [line.split(':', 1) for line in headers.splitlines()]
        if isinstance(headers, list):
            headers = dict(headers)

        cdisp = headers.get("Content-Disposition")
        if not cdisp:
            return None

        cdtype = cdisp.split(';')
        if len(cdtype) == 1:
            return None
        if cdtype[0].strip().lower() not in ('inline', 'attachment'):
            return None

        # several filename params is illegal, but just in case
        fnames = [x for x in cdtype[1:] if x.strip().startswith('filename=')]
        if len(fnames) > 1:
            return None

        name = fnames[0].split('=')[1].strip(' \t"')
        name = os.path.basename(name)
        if not name:
            return None
        return name

    @classmethod
    def from_any(cls, dst=None, headers=None, url=None):
        return dst or cls.from_headers(headers) or cls.from_url(url)


# http://bitbucket.org/techtonik/python-wget/
def download(url, dst=None):
    """
    High level function, which downloads URL into tmp file in current
    directory and then renames it to filename autodetected from either URL
    or HTTP headers.

    url: which url to download
    dst: filename or directory of destination
    """
    # detect of dst is a directory
    dst_ = None
    if dst and os.path.isdir(dst):
        dst_ = dst
        dst = None

    # get filename for temp file in current directory
    prefix = FileName.from_any(dst=dst, url=url)
    fd, tmpfile = tempfile.mkstemp(".tmp", prefix=prefix, dir=".")
    os.close(fd)
    os.unlink(tmpfile)

    if PY2:
        binurl = url
    else:
        # Python 3 can not quote URL as needed
        binurl = list(urlparse.urlsplit(url))
        binurl[2] = urlparse.quote(binurl[2])
        binurl = urlparse.urlunsplit(binurl)
    tmpfile, headers = ulib.urlretrieve(binurl, tmpfile)
    filename = FileName.from_any(dst=dst, headers=headers, url=url)
    if dst_:
        filename = os.path.join(dst_, filename)

    if os.path.exists(filename):
        os.unlink(filename)
    shutil.move(tmpfile, filename)

    return filename