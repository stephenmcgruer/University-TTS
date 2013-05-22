import robotexclusionrulesparser
import time
import threading
import urlparse


class InvalidDomainError(Exception):
  """Exception raised when the domain does not make sense."""
  def __init__(self, domain):
    self.domain = domain


class RobotsTxt(object):
  """A class representing a robots.txt file."""

  def __init__(self, domain, user_agent):
    self.parser = robotexclusionrulesparser.RobotExclusionRulesParser()
    self.parser.user_agent = user_agent
    self.parser.fetch("http://%s/robots.txt" % domain)
    self.last_crawled_time = 0

  def is_allowed(self, url):
    return self.parser.is_allowed(self.parser.user_agent, url)

  def get_crawl_delay(self):
    return self.parser.get_crawl_delay(self.parser.user_agent)

  def update_crawl_time(self):
    self.last_crawled_time = time.time()


class RobotsController(object):
  """A class that holds robots.txt parsers."""

  def __init__(self, user_agent):
    self.user_agent = user_agent
    self.robot_parsers = {}
    self.robot_parser_lock = threading.Lock()

  def get_crawl_delay(self, url):
    """Get the crawl delay for a url."""
    components = urlparse.urlparse(url)
    if not components.netloc:
      raise InvalidDomainError(components.netloc)

    with self.robot_parser_lock:
      self._add_parser_if_missing(url)

    return self.robot_parsers[components.netloc].get_crawl_delay()

  def get_last_crawled(self, url):
    """Get the last crawl time for a url."""
    components = urlparse.urlparse(url)
    if not components.netloc:
      raise InvalidDomainError(components.netloc)

    with self.robot_parser_lock:
      self._add_parser_if_missing(url)

    return self.robot_parsers[components.netloc].last_crawled_time
  
  def crawl_finished(self, url):
    """Notify the robot controller that a crawl has finished for a url."""
    components = urlparse.urlparse(url)
    if components.netloc in self.robot_parsers:
      self.robot_parsers[components.netloc].update_crawl_time()

  def can_fetch(self, url):
    """Check if a url can be fetched based on the domain's robots.txt file."""
    components = urlparse.urlparse(url)
    if not components.netloc:
      raise InvalidDomainError(components.netloc)

    with self.robot_parser_lock:
      self._add_parser_if_missing(url)

    return self.robot_parsers[components.netloc].is_allowed(url)

  def _add_parser_if_missing(self, url):
    """Adds a parser to the dictionary if it isnt already there.

    You must acquire the robot_parser_lock before calling!"""
    components = urlparse.urlparse(url)
    if not components.netloc:
      raise InvalidDomainError(components.netloc)

    if not components.netloc in self.robot_parsers:
      self.robot_parsers[components.netloc] = RobotsTxt(components.netloc, 
          self.user_agent)
