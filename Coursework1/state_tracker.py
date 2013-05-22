from __future__ import with_statement

import numpy as np
import matplotlib.pyplot as plt
import time
import threading

import pickle

class StateTracker(object):
  """Mostly data class for tracking the crawl state and doing statistics.

  Many methods are threadsafe; where not, the method documentation will
  state it.

  Note: for timing the crawl, the crawl is assumed to have started once
  you have created the StateTracker() object."""

  def __init__(self):
    self._crawls = 0
    self._crawls_lock = threading.Lock()

    self._content_urls = set()
    self._total_content_urls = 0
    self._other_urls = set()
    self._total_other_urls = 0
    self._urls_lock = threading.Lock()

    self._total_private_pages = 0
    self._private_pages = set()
    self._private_pages_lock = threading.Lock()

    self._total_other_domains = 0
    self._other_domains = set()
    self._other_domains_lock = threading.Lock()

    self._fetch_errors = {}
    self._fetch_errors_lock = threading.Lock()

    self._parse_errors = 0
    self._parse_errors_lock = threading.Lock()

    self._new_urls_histogram = [0]
    self._url_count_lock = threading.Lock()

    # For timing the crawl.
    self._before = time.time()

  def get_crawl_count(self):
    return self._crawls

  def register_crawl(self):
    with self._crawls_lock:
      self._crawls += 1

  def register_urls_found(self, content_urls, other_urls):
    with self._urls_lock:
      self._total_content_urls += len(content_urls)
      self._total_other_urls += len(other_urls)

      self._content_urls = self._content_urls.union(content_urls)
      self._other_urls = self._other_urls.union(other_urls)

  def register_failed_crawl(self, http_error):
    code = http_error.code
    with self._fetch_errors_lock:
      if code in self._fetch_errors:
        self._fetch_errors[code] += 1
      else:
        self._fetch_errors[code] = 1

  def register_failed_parse(self):
    with self._parse_errors_lock:
      self._parse_errors += 1

  def register_private_page(self, url):
    with self._private_pages_lock:
      self._total_private_pages += 1
      self._private_pages = self._private_pages.union([url])

  def register_other_domain_url(self, url):
    with self._other_domains_lock:
      self._total_other_domains += 1
      self._other_domains = self._other_domains.union([url])

  def register_new_urls(self, count):
    with self._url_count_lock:
      self._new_urls_histogram.append(self._new_urls_histogram[-1] + count)

  def output_stats(self):
    """Output the statistics.

    Not threadsafe!"""
    crawl_time = time.time() - self._before
    total_urls = self._total_content_urls + self._total_other_urls

    print "Crawled %s pages." % self._crawls

    # URL Information
    print "Total Urls Found:   %s" % total_urls
    print "Content Urls Found: %s" % self._total_content_urls
    print "Other Urls Found:   %s" % self._total_other_urls
    print "Distinct Content Urls: %s" % len(self._content_urls)
    print "Distinct Other Urls: %s" % len(self._other_urls)

    # Error statistics.
    if len(self._fetch_errors) > 0:
      print "Fetch errors encountered: %s" % sum(self._fetch_errors.values())
      for (error_code, count) in self._fetch_errors.iteritems():
        print "\tHTTP %s: %s occurrences" % (error_code, count)
    else:
      print "Fetch errors encountered: 0"

    print "Parse errors encountered: %s" % self._parse_errors

    # Domain/Robots.txt statistics.
    print "Content Urls Out Of Domain (Total): %s" % self._total_other_domains
    print "Content Urls Out Of Domain (Distinct): %s" % len(self._other_domains)
    print "Content Urls Not Allowed To Crawl (Total): %s" % self._total_private_pages
    print "Content Urls Not Allowed To Crawl (Distinct): %s" % len(self._private_pages)

    # Time statistics.
    print "Time Taken (seconds): %s" % crawl_time

    self._plot_heaps(self._new_urls_histogram, k=100, beta=0.4)

  def _plot_heaps(self, data, k = 16, beta = 0.5):
    """Plots a Heaps' law style graph.

    Taken from:
    http://www.inf.ed.ac.uk/teaching/courses/tts/labs/Lab1Support.py"""
    x = 100000
    if len(data) > 0:
      x = len(data)

    HLtokens = np.arange(0, x, 1.0)
    HLtypes = k*HLtokens**beta
    plt.plot(HLtokens, HLtypes, '--')
    
    if len(data) > 0:
      plt.plot(HLtokens, data)

    plt.axis(xmin=0, xmax=x, ymin=0)

    plt.xlabel('Crawls')
    plt.ylabel('Crawlable Urls')
    plt.title('Heaps\' Law')
    plt.legend()
    plt.grid(True)
    plt.show()
