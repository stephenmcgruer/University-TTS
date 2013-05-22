import counter


class Graph(object):
  """Represents a graph of email addresses and the emails between them."""

  # The constant used in PageRank.
  _LAMBDA = 0.8

  def __init__(self, aliases_map=None):
    self.nodes = {}

    # Used to merge aliased nodes.
    self.aliases_map = aliases_map or {}

    # Used to quickly find sink nodes: recipients - senders.
    self.recipients = set()
    self.senders = set()

    self.pagerank_initialized = False
    self.hits_initialized = False

  def add_edge(self, message_id, from_email, to_email):
    """Adds an edge to the graph, creating nodes as required.

    Self-edges are ignored.

    Edges must be added before any pagerank or HITS method is called - any edges
    added afterwards are undefined."""

    # Sort out any aliases.
    if from_email in self.aliases_map:
      from_email = self.aliases_map[from_email]
    if to_email in self.aliases_map:
      to_email = self.aliases_map[to_email]

    if from_email == to_email:
      return

    if from_email not in self.nodes:
      from_node = Node(from_email)
      self.nodes[from_email] = from_node

    if to_email not in self.nodes:
      to_node = Node(to_email)
      self.nodes[to_email] = to_node

    self.nodes[from_email].outs[self.nodes[to_email]] += 1
    self.nodes[from_email].outs_count += 1
    self.nodes[from_email].outs_ids.add(message_id)

    self.nodes[to_email].ins[self.nodes[from_email]] += 1

    self.senders.add(self.nodes[from_email])
    self.recipients.add(self.nodes[to_email])

  def run_pagerank(self, number_iterations=10):
    """Runs number_iterations iterations of PageRank on the graph."""

    if not self.pagerank_initialized:
      self._initialize_pagerank()
      self.pagerank_initialized = True

    # Sanity check.
    summed_pagerank = sum([node.pagerank for node in self.nodes.values()])
    if not (summed_pagerank > 0.99 and summed_pagerank < 1.01):
      print "Initial PageRank sanity check failed! (%s)" % summed_pagerank
      return

    for i in range(number_iterations):
      self._run_pagerank_iteration()

      summed_pagerank = sum([node.pagerank for node in self.nodes.values()])
      if not (summed_pagerank > 0.99 and summed_pagerank < 1.01):
        print("PageRank iteration %s sanity check failed! (%s)" % 
            (i + 1, summed_pagerank))
        return

  def _run_pagerank_iteration(self):
    """Runs a single iteration of PageRank."""

    sink_nodes = self.recipients - self.senders
    S = sum([sink.pagerank for sink in sink_nodes])

    number_nodes = len(self.nodes)

    # The LHS of the PageRank addition is constant for each node, so can be
    # precomputed.
    random_jump_numerator = (1 - Graph._LAMBDA) + (Graph._LAMBDA * S)
    random_jump = random_jump_numerator / number_nodes

    # Calculate new pageranks and store in scratch space.
    for node in self.nodes.values():
      follow = Graph._LAMBDA * \
          sum([n.pagerank / n.outs_count for n in node.ins.elements()])

      node.tmp_pagerank = random_jump + follow

    # Update the actual pageranks.
    for node in self.nodes.values():
      node.pagerank = node.tmp_pagerank

  def _initialize_pagerank(self):
    """Initializes the graph for the PageRank algorithm."""

    number_nodes = len(self.nodes)
    for node in self.nodes.values():
      node.pagerank = 1.0 / number_nodes

  def run_hits(self, number_iterations=10):
    """Runs number_iterations iterations of HITS on the graph."""

    if not self.hits_initialized:
      self._initialize_hits()
      self.hits_initialized = True

    # Sanity checks.
    summed_hub = sum([node.hub_score**2 for node in self.nodes.values()])
    if not (summed_hub > 0.99 and summed_hub < 1.01):
      print "Initial HITS hub sanity check failed! (%s)" % summed_hub
      return

    summed_auth = sum([node.authority**2 for node in self.nodes.values()])
    if not (summed_auth > 0.99 and summed_auth < 1.01):
      print "Initial HITS authority sanity check failed! (%s)" % summed_auth
      return

    for i in range(number_iterations):
      self._run_hits_iteration()

      summed_hub = sum([node.hub_score**2 for node in self.nodes.values()])
      if not (summed_hub > 0.99 and summed_hub < 1.01):
        print("HITS iteration %s hub sanity check failed! (%s)" %
          (i + 1, summed_hub))
        return

      summed_auth = sum([node.authority**2 for node in self.nodes.values()])
      if not (summed_auth > 0.99 and summed_auth < 1.01):
        print("HITS iteration %s authority sanity check failed! (%s)" %
          (i + 1, summed_auth))
        return

  def _run_hits_iteration(self):
    """Runs a single iteration of HITS."""

    # Calculate new hubs.
    normalization = 0
    for node in self.nodes.values():
      node.hub_score = sum([out_node.authority for out_node in node.outs.elements()])
      normalization += node.hub_score**2
    normalization = normalization**0.5
    for node in self.nodes.values():
      node.hub_score = node.hub_score / normalization

    # Calculate new authorities.
    normalization = 0
    for node in self.nodes.values():
      node.authority = sum([in_node.hub_score for in_node in node.ins.elements()])
      normalization += node.authority**2
    normalization = normalization**0.5
    for node in self.nodes.values():
      node.authority = node.authority / normalization

  def _initialize_hits(self):
    """Initializes the graph for the HITS algorithm."""

    number_nodes = len(self.nodes)
    initial_value = number_nodes**0.5
    for node in self.nodes.values():
      node.hub_score = 1.0 / initial_value
      node.authority = 1.0 / initial_value


class Node(object):
  """Basic class representing a node (email address) on the graph."""

  def __init__(self, email_address):
    self.email_address = email_address
    self.ins = counter.Counter()
    # For the out nodes a count makes PageRank faster.
    self.outs = counter.Counter()
    self.outs_count = 0
    self.outs_ids = set()


def process_file(filename, aliases_map=None):
  """Converts a graph file into a Graph() object.

  If given, the aliases_map will be used to merge duplicate nodes.

  Returns a tuple of the number of emails processed and the graph."""

  graph = Graph(aliases_map)
  number_emails = 0

  with open(filename, 'r') as f:
    previous_message_id = ""
    for line in f:
      parts = line.strip().split()

      message_id = parts[0]
      from_email = parts[1]
      to_email = parts[2]

      # Track the distinct number of emails.
      if message_id != previous_message_id:
        number_emails += 1
        previous_message_id = message_id

      graph.add_edge(message_id, from_email, to_email)

  return (number_emails, graph)