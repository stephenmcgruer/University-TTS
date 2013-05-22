import graphs


def _dump_stats(number_emails, graph):
  """Print out statistics on the email graph."""

  print "Total number of emails: %s" % number_emails
  print "Total nodes: %s" % len(graph.nodes)
  print "Number of senders: %s" % len(graph.senders)
  print "Number of recipients: %s" % len(graph.recipients)
  both = graph.recipients.intersection(graph.senders)
  print "Size of intersection: %s" % len(both)
  sanity = len(graph.senders) + len(graph.recipients) - len(both)
  print "Sanity check: %s" % sanity


def _run_pagerank(graph):
  """Run pagerank on the graph, and write the results to pr.txt.

  The PageRank scores are checked against the provided sanity value."""

  print "Running PageRank."
  graph.run_pagerank()

  sanity_value = graph.nodes['jeff.dasovich@enron.com'].pagerank
  if not (sanity_value > 0.0019 and sanity_value < 0.0021):
    print "Post PageRank sanity check failed! (%s)" % sanity_value
    return

  nodes = sorted(graph.nodes.values(), key=lambda x : x.pagerank * -1)[:10]
  with open("pr.txt", "w") as f:
    for node in nodes:
      f.write("%0.8f %s\n" % (node.pagerank, node.email_address))

  print "Done."


def _run_hits(graph):
  """Run HITS on the graph, and write the results to hubs.txt and auth.txt.

  The scores are checked against the provided sanity values."""

  print "Running HITS."
  graph.run_hits()

  hub_sanity = graph.nodes['jeff.dasovich@enron.com'].hub_score
  if not (hub_sanity > 0.0009 and hub_sanity < 0.0011):
    print "Post HTS hub sanity check failed! (%s)" % hub_sanity
    return

  nodes = sorted(graph.nodes.values(), key=lambda x : x.hub_score * -1)[:10]
  with open("hubs.txt", "w") as f:
    for node in nodes:
      f.write("%0.8f %s\n" % (node.hub_score, node.email_address))

  authority_sanity = graph.nodes['jeff.dasovich@enron.com'].authority
  if not (authority_sanity > 0.00020 and authority_sanity < 0.00022):
    print "Post HITS authority sanity check failed! (%s)" % authority_sanity
    return

  nodes = sorted(graph.nodes.values(), key=lambda x : x.authority * -1)[:10]
  with open("auth.txt", "w") as f:
    for node in nodes:
      f.write("%0.8f %s\n" % (node.authority, node.email_address))

  print "Done."


def main():
  """Parse the graph file, and run both PageRank and HITS on it."""

  print "Parsing text file."
  (number_emails, graph) = graphs.process_file("data/graph.txt")

  _dump_stats(number_emails, graph)

  _run_pagerank(graph)

  _run_hits(graph)

  print "Finished!"


if __name__ == "__main__":
  main()