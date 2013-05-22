import counter
import doc
import optparse
import output
import tfidf


class PseudoRelevanceFeedback(object):
  """A (slightly tweaked) implementation of PseudoRelevanceFeedback."""

  # The default value for the "k" constant in tf.idf.
  _K = 0.75

  # The default values for the PRF constants.
  _N_D = 19
  _N_W = 38

  def __init__(self, k, n_d, n_w):
    self.k = k or PseudoRelevanceFeedback._K
    self.n_d = n_d or PseudoRelevanceFeedback._N_D
    self.n_w = n_w or PseudoRelevanceFeedback._N_W

    self.tf_idf = tfidf.TfIdf(self.k)

  def calculate_similarity(self, query_file, data_file, filename):
    """Calculate the similarity between a query file and a data file.

    The results are written to a file named "filename"."""

    queries_set = doc.DocumentSet(query_file)
    documents_set = doc.DocumentSet(data_file)

    results = []
    for query in queries_set.documents:
      # Compute the initial tfidfs.
      initial_tfidfs = self.tf_idf._tfidf(query, documents_set)

      # Select the top n_d scoring documents.
      initial_tfidfs = sorted([(-s, d) for (_, d, s) in initial_tfidfs])
      initial_tfidfs = [(d, -s) for (s, d) in initial_tfidfs[:self.n_d]]
      selected_docs = [document for (document, _) in initial_tfidfs]

      # Combine the top documents into a 'mega document'.
      summed_counter = counter.Counter(query.words_counter)
      for document in selected_docs:
        summed_counter += document.words_counter
      mega_document = doc.document_from_dict(None, dict(summed_counter))

      # Select the top n_w scoring words (via tf.idf) from the megadocument.
      word_scores = []
      for word in sorted(list(mega_document.words_counter)):
        score = self.tf_idf._document_tfidf(word, mega_document, documents_set)
        word_scores.append((-score, word))
      word_scores = sorted(word_scores)[:self.n_w]
      word_scores = [(word, -score) for (score, word) in word_scores]

      # Use these new words as the next query, and return the tf.idf scores.
      new_query = doc.document_from_dict(query.id, dict(word_scores))
      results.extend(self.tf_idf._tfidf(new_query, documents_set))

    output.write_output_file(filename, results)


def main():
  """Calculates the tf.idf similarity between qrys.txt & docs.txt, with PRF.

  The results are written out to the file "best.top"."""

  parser = optparse.OptionParser()
  parser.add_option("-k",
      type="float",
      action="store",
      dest="k",
      default=None,
      help="The value of the constant used in tf.idf.")
  parser.add_option("-d", "--number-documents",
      type="int",
      action="store",
      dest="n_d",
      default=None,
      help="The maximum number of documents to select from the list PRF uses.")
  parser.add_option("-w", "--number-words",
      type="int",
      action="store",
      dest="n_w",
      default=None,
      help="The maximum number of words PRF takes from each document.")
  (options, args) = parser.parse_args()

  query_file = "data/qrys.txt"
  data_file = "data/docs.txt"

  prf = PseudoRelevanceFeedback(options.k, options.n_d, options.n_w)
  prf.calculate_similarity(query_file, data_file, "best.top")


if __name__ == "__main__":
  main()
