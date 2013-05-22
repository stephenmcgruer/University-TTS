import collections
import counter
import math
from nltk.corpus import stopwords
import string
import warnings


# The DICE version of nltk is old and has a deprecation warning. Ignore it.
with warnings.catch_warnings():
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  _stopwords = set(stopwords.words('english'))


class EmailSet(object):
  """Represents a set of emails."""

  def __init__(self):
    self.emails = set()
    self.number_emails = 0
    self.total_length = 0
    self.inverted_index = collections.defaultdict(set)

  def add_email(self, email):
    self.emails.add(email)
    self.number_emails += 1
    self.total_length += email.length
    for word in email.words_counter:
      self.inverted_index[word].add(email)

  def avg_length(self):
    return float(self.total_length) / self.number_emails

  def best_tfidf(self):
    """Find the best word according to tf.idf.

    Not used for reasons explained in the report."""

    for (i, email) in enumerate(self.emails):
      print "\t%s" % i
      email.tfidf = counter.Counter()
      for word in email.words_counter:
        tf_d = email.words_counter[word]
        df = len(self.inverted_index[word])
        idf = math.log(self.number_emails / float(df))
        squasher = float(2 * email.length) / self.avg_length()
        score = (tf_d / (tf_d + squasher)) * idf

        email.tfidf[word] = score

    overall_tfidfs = counter.Counter()
    for email in self.emails:
      overall_tfidfs += email.tfidf

    return overall_tfidfs.most_common(1)[0][0]


class Email(object):
  """Represents an email."""

  def __init__(self, email_id, wiki_words):
    self.id = email_id
    self._subject = None
    self.length = 0
    self.words_counter = counter.Counter()
    self.wiki_words = wiki_words

  @property
  def subject(self):
    return self._subject

  @subject.setter
  def subject(self, value):
    value = value.lower()
    value = value.replace('re: ', '')
    value = value.replace('fw: ', '')
    value = value.replace('re ', '')
    value = value.replace('fw ', '')
    value = value.strip()
    value = value.translate(string.maketrans("",""), string.punctuation)
    if value == 're' or value == 'fw':
      value = ""

    value = value.split()
    value = [word for word in value if word not in _stopwords]
    value = [word for word in value if not word.isdigit()]
    value = [word for word in value if word in self.wiki_words]

    if len(value):
      self._subject = value

  def add_line(self, line):
    words = line.split()
    words = [word for word in words if word in self.wiki_words]
    words = [word for word in words if not word.isdigit()]

    self.length += len(words)
    self.words_counter.update(words)