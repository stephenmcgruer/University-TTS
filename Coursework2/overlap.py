import doc
import counter
import itertools
import output

def _calculate_overlap(query, inverted_index):
  """Calculate the overlaps between a query and all documents.

  An inverted index is used so that only the documents containing
  the query words are examined."""

  # Counts the number of each document in the inverted index for each
  # word in the query. That is, if the query was "bob marley" and we
  # had {"bob" -> [d1, d4, d6], "marley" -> [d2, d4, d5]}, the result
  # would be a counter of {d1:1, d2:1, d4:2, d5:1, d6:1}.
  document_overlaps = counter.Counter()
  for word in query.words_counter:
    document_overlaps.update(inverted_index[word])

  return [(query, d, score) for (d, score) in document_overlaps.most_common()]


def main():
  """Calculates the basic word overlap similarity between qrys.txt & docs.txt.

  The results are written out to the file 'overlap.top'."""

  query_file = 'data/qrys.txt'
  data_file = 'data/docs.txt'
  
  queries_set = doc.DocumentSet(query_file)
  documents_set = doc.DocumentSet(data_file)

  results = []
  for query in queries_set.documents:
    results.extend(_calculate_overlap(query, documents_set.inverted_index))

  # Output the overlaps.
  output.write_output_file('overlap.top', results)


if __name__ == "__main__":
  main()