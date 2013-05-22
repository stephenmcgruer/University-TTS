import collections
import doc
import itertools
import math
import output

class TfIdf(object):

  # The default value for the 'k' constant in tf.idf.
  _K = 2

  def __init__(self, k=None):
    if k is None:
      k = TfIdf._K
    self.k = k

  def _document_tfidf(self, word, document, doc_set):
    """Calculates the tf.idf for a document (without the tf_q term)."""
    tf_d = document.words_counter[word]
    df = len(doc_set.inverted_index[word])

    # log(|C| / df_w)
    idf = math.log(doc_set.number_documents / float(df))

    # (k|D| / avg|D|)
    squasher = float(self.k * document.length) / doc_set.avg_length

    # (tf_w,D / (tf_w,D + ((k|D| / avg|D|))) * log(|C| / df_w)
    return (tf_d / (tf_d + squasher)) * idf

  def _tfidf(self, query, document_set):
    """Calculates the similarity between a query and all applicable documents.

    An inverted index is used to look up the relevant documents for a query."""

    document_tfidfs = collections.defaultdict(float)

    for (word, tf_q) in query.words_counter.most_common():
      matching_documents = document_set.inverted_index[word]

      for document in matching_documents:
        document_tfidfs[document] += tf_q * self._document_tfidf(
            word, document, document_set)

    return [(query, d, score) for (d, score) in document_tfidfs.items()]

  def calculate_similarity(self, query_file, data_file, filename, k=None):
    """Calculate the similarity between a query file and a data file.

    The results are written to a file named 'filename'."""

    queries_set = doc.DocumentSet(query_file)
    documents_set = doc.DocumentSet(data_file)

    results = []
    for query in queries_set.documents:
      results.extend(self._tfidf(query, documents_set))

    output.write_output_file(filename, results)


def main():
  """Calculates the tf.idf similarity between qrys.txt & docs.txt.

  The results are written out to the file 'tfidf.top'."""

  query_file = 'data/qrys.txt'
  data_file = 'data/docs.txt'

  tf_idf = TfIdf()
  tf_idf.calculate_similarity(query_file, data_file, 'tfidf.top')

if __name__ == "__main__":
  main()