import time

class TimeoutManager:
  """A very basic class for deciding how often a url should be crawled..

  Because we have static content, always returns 'never'."""

  def get_timeout(self, url):
    """Returns the time that a url should be crawled again.

    To decide if this url should be crawled, pass the returned
    value from this function to timeout_passed()."""

    # None represents 'never crawl again'.
    return None

  def timeout_passed(self, timeout):
    """Returns true if the given timeout has passed, false otherwise.

    Note that 'None' has a special value for this function, so passing
    it in may confuse you!"""
    return time.time() > timeout and timeout is not None