def write_output_file(name, results):
  """Writes a set of results to an output file.

  The results must be in the form of a list of triples
  (query, document, similarity)."""
  format_string = "%s 0 %s 0 %s 0\n"

  with open(name, 'w') as f:
    for (q, d, similarity) in results:
      f.write(format_string % (q.id, d.id, similarity))