from HTMLParser import HTMLParser as _HTMLParser, HTMLParseError, \
                       attrfind, endendtag, endtagfind, tagfind
import sys

HTMLParseError = HTMLParseError

# The fix is only needed on Python before 2.7.3 (or for 3.2ish, but who uses
# Python 3 anyway? ;).)
if sys.version_info >= (2,7,3):
  HTMLParser = _HTMLParser
else:
  class HTMLParser(_HTMLParser):
    """Patched version of HTMLParser with fixed cdata handling.

    NOTE: The patched changes in this are NOT my work. See
    http://bugs.python.org/issue670664 for the source."""

    def reset(self):
      self.cdata_elem = None
      _HTMLParser.reset(self)

    def set_cdata_mode(self, elem):
      self.cdata_elem = elem.lower()
      _HTMLParser.set_cdata_mode(self)

    def clear_cdata_mode(self):
      self.cdata_elem = None
      _HTMLParser.clear_cdata_mode(self)

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag(self, i):
      self.__starttag_text = None
      endpos = self.check_for_whole_start_tag(i)
      if endpos < 0:
        return endpos
      rawdata = self.rawdata
      self.__starttag_text = rawdata[i:endpos]

      # Now parse the data between i+1 and j into a tag and attrs
      attrs = []
      match = tagfind.match(rawdata, i+1)
      assert match, 'unexpected call to parse_starttag()'
      k = match.end()
      self.lasttag = tag = rawdata[i+1:k].lower()

      while k < endpos:
        m = attrfind.match(rawdata, k)
        if not m:
          break
        attrname, rest, attrvalue = m.group(1, 2, 3)
        if not rest:
          attrvalue = None
        elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
             attrvalue[:1] == '"' == attrvalue[-1:]:
          attrvalue = attrvalue[1:-1]
          attrvalue = self.unescape(attrvalue)
        attrs.append((attrname.lower(), attrvalue))
        k = m.end()

      end = rawdata[k:endpos].strip()
      if end not in (">", "/>"):
        lineno, offset = self.getpos()
        if "\n" in self.__starttag_text:
          lineno = lineno + self.__starttag_text.count("\n")
          offset = len(self.__starttag_text) \
                   - self.__starttag_text.rfind("\n")
        else:
          offset = offset + len(self.__starttag_text)
        self.error("junk characters in start tag: %r"
                   % (rawdata[k:endpos][:20],))
      if end.endswith('/>'):
        # XHTML-style empty tag: <span attr="value" />
        self.handle_startendtag(tag, attrs)
      else:
        self.handle_starttag(tag, attrs)
        if tag in self.CDATA_CONTENT_ELEMENTS:
          self.set_cdata_mode(tag)
      return endpos

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag(self, i):
      rawdata = self.rawdata
      assert rawdata[i:i+2] == "</", "unexpected call to parse_endtag"
      match = endendtag.search(rawdata, i+1) # >
      if not match:
        return -1
      j = match.end()
      match = endtagfind.match(rawdata, i) # </ + tag +  >
      if not match:
        if self.cdata_elem is not None:
          self.handle_data(rawdata[i:j])
          return j
        self.error("bad end tag: %r" % (rawdata[i:j],))

      elem = match.group(1).lower() # script or style
      if self.cdata_elem is not None:
        if elem != self.cdata_elem:
          self.handle_data(rawdata[i:j])
          return j

      self.handle_endtag(elem)
      self.clear_cdata_mode()
      return j
