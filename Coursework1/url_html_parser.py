from html_parser import *

class UrlHTMLParser(HTMLParser):
  """Parses a HTML document, extracting urls.

  The urls must be the target of an '<a ...> ... </a>' style anchor tag to be
  discovered. Discovered urls are split into those within a <!--- CONTENT --->
  block and those not.

  The urls are saved as found and not post-processed at all, so may be relative
  or absolute."""

  def __init__(self):
    HTMLParser.__init__(self)

    self._in_content_block = False
    self._urls = []

  def handle_starttag(self, tag, attributes):
    tag = tag.strip().lower()
    if tag == "a":
      for (attribute, content) in filter(lambda x : x[0] == 'href', attributes):
        self._urls.append((content, self._in_content_block))

  def handle_startendtag(self, tag, attributes):
    # Do nothing, as per point 2 of the 'Questions and Answers' section
    # of the coursework:
    # "You should only follow anchor tags of the form: <a ...> ... </a>"

    # I may be being overly-literal, but hey, why not :).
    pass

  def handle_comment(self, comment):
    comment = comment.strip()
    if comment == "CONTENT":
      self._in_content_block = True
    elif comment == "/CONTENT":
      self._in_content_block = False

  def GetAllUrls(self):
    return self._urls

  def GetContentUrls(self):
    return [url for (url, in_content) in self._urls if in_content]

  def GetOtherUrls(self):
    return [url for (url, in_content) in self._urls if not in_content]

  def GetNumberOfUrls(self):
    return len(self._urls)