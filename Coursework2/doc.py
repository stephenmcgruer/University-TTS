import collections
from counter import Counter


class DocumentSet(object):
  """Represents a set of documents (or queries!)"""

  def __init__(self, document_filename):
    with open(document_filename, 'r') as f:
      lines = f.readlines()

    self.documents = []
    self.inverted_index = collections.defaultdict(set)
    for line in lines:
      parts = line.split()
      document_id = int(parts.pop(0))

      document = Document(document_id, parts)
      self.documents.append(document)
      for word in parts:
        self.inverted_index[word].add(document)

    self.number_documents = len(self.documents)

    total_length = sum([document.length for document in self.documents])
    self.avg_length = float(total_length) / self.number_documents


class Document(object):
  """Represents a document (or query!)."""

  def __init__(self, document_id, document_words):
    self.id = document_id
    self.length = len(document_words)
    self.words_counter = Counter(document_words)

  def update(self, update_counter):
    """Will upset the DocumentSet average length!"""

    self.words_counter.update(update_counter)
    self.length = sum(self.words_counter.values())


def document_from_dict(the_id, the_dict):
  d = Document(the_id, the_dict)
  d.length = sum(the_dict.values())
  return d