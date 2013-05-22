from __future__ import with_statement

import itertools
import logging
import optparse
import Queue
import re
import robots_controller
import state_tracker
import time
import timeout_manager
import threading
import urllib2
import urlparse
from url_html_parser import UrlHTMLParser, HTMLParseError


# The module logger. The handler will capture everything above and including
# DEBUG level.
_logger = logging.getLogger(__name__)
_handler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG)
_logger.addHandler(_handler)


class Crawler(object):
  """The main crawler."""

  USER_AGENT = 'TTS'

  SEED_DOMAIN = 'ir.inf.ed.ac.uk'
  SEED_URL = 'http://ir.inf.ed.ac.uk/tts/A1/0840449/0840449.html'

  # Whitelist of allowed domains. Not threadsafe - do not edit in a thread!
  ALLOWED_DOMAINS = set([SEED_DOMAIN])

  # The number of seconds a thread should block on a queue before trying again.
  QUEUE_TIMEOUT = 2

  def __init__(self, options):
    self.domains_queue = Queue.Queue()
    self.data_queue = Queue.Queue()
    self.robots_controller = robots_controller.RobotsController(Crawler.USER_AGENT)

    self.seen_urls = {}
    self.domains_dict = {}
    # This lock controls access to both seen_urls and domains_dict. If you want
    # to add items to either dictionary, you *must* acquire this lock first. 
    self.dictionaries_lock = threading.Lock()

    # This flag is used to indicate to the fetcher and parser threads that
    # the crawling is over.
    self.finished_crawling_flag = threading.Event()

    # User controlled options.
    self.number_fetch_threads = options.number_fetch_threads
    self.number_parse_threads = options.number_parse_threads
    self.obey_crawl_delay = options.obey_crawl_delay

    # Used to decide when a url should be crawled again.
    self.url_timeout_manager = timeout_manager.TimeoutManager()

    # Due to the (very poor, imo) implementation of priority queues, the
    # simplest way to do a max-value priority queue is to negate the
    # priority values.
    seed_domain_queue = Queue.PriorityQueue()
    seed_domain_queue.put((-840449, self.SEED_URL))
    seed_timeout = self.url_timeout_manager.get_timeout(self.SEED_URL)
    self.seen_urls[840449] = (self.SEED_URL, seed_timeout)

    self.domains_queue.put(seed_domain_queue)
    self.domains_dict[self.SEED_DOMAIN] = seed_domain_queue

  def crawl(self):
    """Crawl the web!

    Pages are crawled until (roughly speaking) both the domain and data queues
    are 'true' empty (that is, they have no tasks left), which signifies that
    there are no more unique urls to crawl.

    Note that pages are not crawled more than once, since we're dealing with 
    static content."""

    self.state = state_tracker.StateTracker()

    # Start the fetcher and parser threads.
    for i in range(self.number_fetch_threads):
      fetch_thread = DataFetchingThread(i, self.domains_queue, self.data_queue,
          self.robots_controller, self.finished_crawling_flag, self.state,
          self.obey_crawl_delay)
      fetch_thread.setDaemon(True)
      fetch_thread.start()

    for i in range(self.number_parse_threads):
      parse_thread = DataParsingThread(i, self.domains_queue,
          self.domains_dict, self.data_queue, self.robots_controller,
          self.seen_urls, self.dictionaries_lock, self.finished_crawling_flag,
          self.state, self.url_timeout_manager)
      parse_thread.setDaemon(True)
      parse_thread.start()

    # Bit of a hack, but it's nice to force a context switch and let the
    # workers get working.
    time.sleep(2)

    # This isn't perfect, but it's surprisingly difficult to wait on two queues
    # that are not directly linked, where one has more nested queues... yeah,
    # needless to say it gets complicated.
    while True:
      self.data_queue.join()
      domain_queues_empty = len(
          [1 for queue in self.domains_dict.values() if not queue.empty()]) == 0
      if self.data_queue.empty() and domain_queues_empty:
        break
      time.sleep(1)

    _logger.info("Done!")
    self.finished_crawling_flag.set()
    self.state.output_stats()


class DataFetchingThread(threading.Thread):
  """Threaded data fetching.

  While the finished_crawling_flag has not been set, will attempt to pop urls
  from the url_queue, and download the data from the webpage."""

  def __init__(self, name, domain_queues, data_queue, robots_controller,
      finished_crawling_flag, state, obey_crawl_delay):
    threading.Thread.__init__(self)
    self.name = name
    self.domain_queues = domain_queues
    self.data_queue = data_queue
    self.robots_controller = robots_controller
    self.finished_crawling_flag = finished_crawling_flag
    self.state = state
    self.obey_crawl_delay = obey_crawl_delay

  def run(self):
    while not self.finished_crawling_flag.is_set():
      # Grab a domain.
      try:
        _logger.debug("[fetcher %s] Waiting for domain.", self.name)
        domain_queue = self.domain_queues.get(timeout=Crawler.QUEUE_TIMEOUT)
        _logger.debug("[fetcher %s] Got domain.", self.name)
      except Queue.Empty:
        # No domain available; loop around and try 
        # again!
        _logger.debug("[fetcher %s] No domain available.", self.name)
        continue

      # If we don't need to be nice, just stick the domain queue back on for
      # other threads to play with.
      if not self.obey_crawl_delay:
        self.domain_queues.put(domain_queue)
        _logger.debug("[fetcher %s] Replaced domain.", self.name)
        self.domain_queues.task_done()

      # Grab a url for the domain.
      try:
        _logger.debug("[fetcher %s] Waiting for url.", self.name)
        (_, url) = domain_queue.get(timeout=Crawler.QUEUE_TIMEOUT)
        _logger.debug("[fetcher %s] Got url: %s", self.name, url)
      except Queue.Empty:
        # No url available; loop around and try again!
        _logger.debug("[fetcher %s] No url available.", self.name)
        if self.obey_crawl_delay:
          self.domain_queues.put(domain_queue)
          _logger.debug("[fetcher %s] Replaced domain.", self.name)
          self.domain_queues.task_done()
        continue

      self.state.register_crawl()
      components = urlparse.urlparse(url)
      
      if self.obey_crawl_delay:
        crawl_delay = self.robots_controller.get_crawl_delay(url)
        last_crawled = self.robots_controller.get_last_crawled(url)

        # Wait for the delay to be over. Ideally we would actually just grab a
        # different URL to crawl instead while waiting, but given that we only
        # have one host in the coursework, that was a layer of complexity I
        # just couldn't face.
        difference = time.time() - last_crawled
        _logger.debug("[fetcher %s] Obeying crawl delay: waiting %s seconds.",
            self.name, difference)
        while crawl_delay > 0 and difference < crawl_delay:
          time.sleep(difference)
          difference = time.time() - last_crawled

      _logger.info("[fetcher %s] Crawling %s", self.name, url)

      request = urllib2.Request(url)
      request.add_header('User-Agent', Crawler.USER_AGENT)
      opener = urllib2.build_opener()
      try:
        data = opener.open(request).read()
        self.data_queue.put((url, data))
      except urllib2.HTTPError as http_error:
        self.state.register_failed_crawl(http_error)

      self.robots_controller.crawl_finished(url)

      domain_queue.task_done()

      # Put the domain back if necessary.
      if self.obey_crawl_delay:
        self.domain_queues.put(domain_queue)
        _logger.debug("[fetcher %s] Replaced domain.", self.name)
        self.domain_queues.task_done()


class DataParsingThread(threading.Thread):
  """Threaded data parsing.

  While the finished_crawling_flag flag has not been set, will attempt to
  pop data from the data_queue, and parse the webpage to find content urls."""

  def __init__(self, name, domains_queue, domains_dict, data_queue, 
      robots_controller, seen_urls, dictionaries_lock, finished_crawling_flag,
      state, url_timeout_manager):
    threading.Thread.__init__(self)
    self.name = name
    self.domains_queue = domains_queue
    self.domains_dict = domains_dict
    self.data_queue = data_queue
    self.robots_controller = robots_controller
    self.seen_urls = seen_urls
    self.dictionaries_lock = dictionaries_lock
    self.finished_crawling_flag = finished_crawling_flag
    self.state = state
    self.url_timeout_manager = url_timeout_manager

  def run(self):
    while not self.finished_crawling_flag.is_set():
      try:
        _logger.debug("[parser %s] Waiting for source url.", self.name)
        (source_url, data) = self.data_queue.get(timeout=Crawler.QUEUE_TIMEOUT)
        _logger.debug("[parser %s] Got url.", self.name)
      except Queue.Empty:
        # Nothing on the data queue; loop around and try again.
        _logger.debug("[parser %s] No url available.", self.name)
        continue

      source_components = urlparse.urlparse(source_url)

      _logger.debug("[parser %s] Parsing page %s", self.name, source_url)

      try:
        parser = UrlHTMLParser()
        parser.feed(data)
        urls = parser.GetContentUrls()
        other_urls = parser.GetOtherUrls()
      except HTMLParseError as e:
        # Fall back on regex.
        self.state.register_failed_parse()
        urls, other_urls = self.regex_parse(data)

      self.state.register_urls_found(urls, other_urls)

      new_urls_count = 0
      for url in urls:
        components = urlparse.urlparse(url)

        # No scheme means that it was a relative url.
        if not components.scheme:
          url = self.fix_relative_url(url, source_components)
          components = urlparse.urlparse(url)

        domain = components.netloc
        if domain not in Crawler.ALLOWED_DOMAINS:
          _logger.debug("[parser %s] Domain %s not allowed", self.name, domain)
          self.state.register_other_domain_url(url)
          continue

        if self.robots_controller.can_fetch(url):
          # URLs are identified by the number at the end of their path.
          url_priority = self.extract_identifier(url)
          with self.dictionaries_lock:
            if self.should_crawl(url_priority):
              _logger.debug("[parser %s] New url seen: %s.", self.name, url)
              new_urls_count += 1
              self.seen_urls[url_priority] = (url, 
                  self.url_timeout_manager.get_timeout(url))

              # Add the domain if it isn't already being tracked.
              if not domain in self.domains_dict:
                _logger.debug("[parser %s] New domain seen: %s.", self.name,
                    domain)
                new_domain_queue = Queue.PriorityQueue()
                self.domains_dict[domain] = new_domain_queue
                self.domains_queue.put(new_domain_queue)

              # Put the url on the domain queue.
              self.domains_dict[domain].put((-url_priority, url))
        else:
          self.state.register_private_page(url)

      self.state.register_new_urls(new_urls_count)
      self.data_queue.task_done()

  def regex_parse(self, data):
    """Parse a webpage using basic regular expressions to find links.

    A quite basic fallback in case HTMLParser throws an error. Will attempt to
    find urls in <a> tags in both CONTENT and non-CONTENT sections
    (differentiating between the sections)."""

    opening_split = data.split('<!-- CONTENT -->')
    fully_split = [ part.split('<!-- /CONTENT -->') for part in opening_split]
    # Flatten the list of lists.
    fully_split = list(itertools.chain.from_iterable(fully_split))

    content_data = ' '.join(fully_split[1::2])
    other_data = ' '.join(fully_split[::2])

    regex = '<a.*?href=["\']([^"]+[.\s]*?)["\'].*?>[^<]+[.\s]*?</a>'
    content_urls = re.findall(regex, content_data)
    other_urls = re.findall(regex, other_data)

    return content_urls, other_urls

  def fix_relative_url(self, url, source_components):
    """Takes a relative url and makes it absolute using components of a source.

    For example, if the url is '1234567.html' and the source url is something
    like 'http://ir.inf.ed.ac.uk/tts/A1/0840449/0840449.html', returns the url
    'http://ir.inf.ed.ac.uk/tts/A1/0840449/1234567.html'."""

    path_parts = source_components.path.split('/')
    path_parts[-1] = url
    new_path = '/'.join(path_parts)

    return ("%s://%s%s" %
        (source_components.scheme, source_components.netloc, new_path))

  def extract_identifier(self, url):
    """Extracts the page identifier from the url.

    For example, an input 'http://ir.inf.ed.ac.uk/tts/A1/0840449/1234567.html'
    should produce the output '1234567'."""

    path = urlparse.urlparse(url).path
    html_stripped_path = path.split('.')[0]
    identifier = html_stripped_path.split('/')[-1]

    return int(identifier)

  def should_crawl(self, url_priority):
    """Determine if a given url should be crawled.

    The decision is made based on whether the url has been seen before, and if
    so, whether or not it's timeout has passed.

    Note: You *MUST* hold the dictionaries_lock lock before calling this function
    for guaranteed correctness!"""
    if url_priority in self.seen_urls:
      timeout = self.seen_urls[url_priority][1]
      return self.url_timeout_manager.timeout_passed(timeout)

    # Url has never been seen, we should crawl it.
    return True

def main():
  parser = optparse.OptionParser()
  parser.add_option("--obey_crawl_delay", action="store_true", default=False,
      dest="obey_crawl_delay", help="Obey the crawl delay directive.")
  parser.add_option("--number_fetch_threads", type="int", default=0,
      dest="number_fetch_threads",
      help="Set the number of URL fetching threads to use.")
  parser.add_option("--number_parse_threads", type="int", default=0,
      dest="number_parse_threads",
      help="Set the number of parsing threads to use.")
  parser.add_option("--log_level", type="choice", default="INFO",
      choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
      dest="log_level", help="Set the level of logs to show.")

  (options, args) = parser.parse_args()

  # There's little point multi-threading the crawler if we're obeying
  # the crawl delay.
  if options.obey_crawl_delay and options.number_fetch_threads > 1:
    decision = ''
    answers = ['k', 's', 'q']
    print("WARNING: You have set obey_crawl_delay, but also chosen to use "
          "multiple fetcher threads. Since we only have one site to crawl, "
          "most of the fetcher threads may do nothing.\n\n"
          "Do you want to [k]eep using %s threads, use [s]equential crawling "
          "instead, or [q]uit?" % options.number_fetch_threads)
    while decision not in answers:
      decision = raw_input("? ").lower()
      if decision not in answers:
        print "Unrecognized option %s, please try again." % decision

    if decision == 'q':
      return
    elif decision == 's':
      options.number_fetch_threads = 1

  # Set the default number of fetch threads if the user hasn't, based
  # on whether we're obeying the crawl delay or not.
  if options.obey_crawl_delay:
    options.number_fetch_threads = options.number_fetch_threads or 1
    options.number_parse_threads = options.number_parse_threads or 1
  else:
    options.number_fetch_threads = options.number_fetch_threads or 3
    options.number_parse_threads = options.number_parse_threads or 3

  # Python2.6 doesnt seem to like setLevel(str), so we'll do this manually.
  if options.log_level == 'DEBUG':
    _logger.setLevel(logging.DEBUG)
  elif options.log_level == 'INFO':
    _logger.setLevel(logging.INFO)
  elif options.log_level == 'WARNING':
    _logger.setLevel(logging.WARNING)
  elif options.log_level == 'ERROR':
    _logger.setLevel(logging.ERROR)
  elif options.log_level == 'CRITICAL':
    _logger.setLevel(logging.CRITICAL)
  else:
    print "Unknown logging level %s!" % options.log_level
    return

  crawler = Crawler(options)
  crawler.crawl()

if __name__ == '__main__':
  main()
