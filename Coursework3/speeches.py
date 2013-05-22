import collections
import counter
import finn
from itertools import izip_longest
import os
import simhash
import string
import zlib


def grouper(n, iterable, padvalue=None):
  """Chunks an iterable into 'n' sized chunks, with padding if necessary.

  Taken from http://stackoverflow.com/questions/312443/how-do-you-split-
  a-list-into-evenly-sized-chunks-in-python
  """

  return izip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


class Speech:
  """Represents a single speech."""

  # Used in the calculation of adler32.
  _LARGE_PRIME = 65521

  def __init__(self, file_id, text, use_zlib, bit_size):
    self.id = file_id

    self.tokens = text.split()
    token_counter = counter.Counter(self.tokens)

    self.exact_fingerprint = self._adler_32(text, use_zlib)

    self.near_fingerprint = simhash.hash(token_counter, bit_size)
    self.near_fingerprint_buckets = []

    self.plateau_fingerprint = None
    self.plateau_fingerprint_buckets = []
    plateau = finn.find_plateau(self.tokens)
    if plateau is not None:
      plateau_counter = counter.Counter(plateau)
      self.plateau_fingerprint = simhash.hash(plateau_counter, bit_size)

  def _adler_32(self, text, use_zlib):
    """Compute the adler32 checksum of a block of text.

    If use_zlib is set, just return zlib.adler32(...), otherwise calculate it
    manually."""

    if use_zlib:
      return zlib.adler32(text)
    else:
      # It was noted on the forums by Dr Lavrenko that we did not need to
      # implement adler32, so using zlib's version should be fine. However,
      # just for completeness, here is the version I wrote before discovering
      # that.
      a = 0
      b = 0
      for character in text:
        if character == ' ':
          continue

        b += ord(character)
        a += b

      return ((a % Speech._LARGE_PRIME) << 16) | (b % Speech._LARGE_PRIME)


class SpeechSet:
  """Represents a set of speeches."""

  def __init__(self, folder_name, use_zlib=True, bit_size=128,
      use_groups=True):
    """Parses a directory of speeches.

    If use_zlib is set to false, the 'exact' hash will be calculated manually
    instead of via zlib.adler32(...)."""

    if not os.path.isabs(folder_name):
      folder_name = os.path.abspath(folder_name)

    self.speeches = set()
    self.exact_fingerprints = collections.defaultdict(set)

    # The grouped fingerprints are stored as a flat dictionary - the index of
    # the group is prefixed onto keys to indicate which of the L groups a
    # value is. For example, the key '40110' indicates bucket 6 in group 4.
    self.near_fingerprints = collections.defaultdict(set)
    self.plateau_fingerprints = collections.defaultdict(set)

    # Parse the speeches.
    files = os.listdir(folder_name)
    for filename in files:
      speech_file = os.path.join(folder_name, filename)

      # Skip non-text files.
      if not filename.endswith('.txt'):
        continue

      with open(speech_file, 'r') as f:
        lines = [line.strip() for line in f]

      speech_id = self._get_id(filename)
      cleaned_lines = self._clean_text(lines)
      text = ' '.join(cleaned_lines)

      s = Speech(speech_id, text, use_zlib, bit_size)
      self.speeches.add(s)

      # Keep inverted index of exact fingerprints to speeches.
      self.exact_fingerprints[s.exact_fingerprint].add(s)

      # Add each chunk of the near and plateau fingerprints to the
      # appropriate group.
      if use_groups:
        chunked_near_fingerprint = grouper(4, s.near_fingerprint)
        for (i, chunk) in enumerate(chunked_near_fingerprint):
          key = "%s%s" % (i, ''.join(map(str, chunk)))
          self.near_fingerprints[key].add(s)
          s.near_fingerprint_buckets.append(self.near_fingerprints[key])

        if s.plateau_fingerprint is not None:
          chunked_plateau_fingerprint = grouper(4, s.plateau_fingerprint)
          for (i, chunk) in enumerate(chunked_plateau_fingerprint):
            key = "%s%s" % (i, ''.join(map(str, chunk)))
            self.plateau_fingerprints[key].add(s)
            s.plateau_fingerprint_buckets.append(
                self.plateau_fingerprints[key])

  def _get_id(self, name):
    """Extracts the id from a filename."""

    parts = name.split('.')
    return '.'.join(parts[:-1])

  def _clean_text(self, lines):
    """Cleans the text of a speech.

    The text should be given as a list of lines. The cleaning operations that
    are performed are to:
      * Remove the 'This is a speech by...' line at the start.
      * Remove any title line before the main speech.
      * Remove empty lines.
      * Remove punctuation from each line.

    The text is returned as it was given - a list of lines.
    """

    # Skip the 'This is a...' line and the blank line that follows.
    lines = lines[2:]

    # Try and detect the 'I am a' lines. They're generally short.
    if len(lines[0].split()) <= 7:
      lines = lines[1:]

    # Remove any empty lines.
    lines = filter(None, lines)

    # Remove punctuation.
    lines = [self._strip_punctuation(line) for line in lines]

    return lines

  def _strip_punctuation(self, text):
    """Strips punctuation from a string."""

    return text.translate(string.maketrans('', ''), string.punctuation)