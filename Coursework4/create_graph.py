import collections
import counter
import emails
import graphs
import info
import itertools
from nltk.corpus import stopwords
import re
import string
import warnings


# The DICE version of nltk is old and has a deprecation warning. Ignore it.
with warnings.catch_warnings():
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  _stopwords = set(stopwords.words('english'))


class Relation(object):
  """Represents a relationship between two nodes, i.e. a set of emails."""

  def __init__(self, from_info, to_info):
    self.from_info = from_info
    self.to_info = to_info
    self.emails = emails.EmailSet()
    self.words = counter.Counter()
    self.hash = None

  def __eq__(self, other):
    return (other and
        self.from_info == other.from_info and
        self.to_info == other.to_info)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __hash__(self):
    return hash((self.from_info, self.to_info))


def get_interesting_nodes(graph, aliases, n=8):
  """Returns 'interesting' nodes to graph."""

  graph.run_pagerank()
  nodes = sorted(graph.nodes.values(), key=lambda x : x.pagerank * -1)[:n]

  interesting = set()
  for node in nodes:
    interesting.add(node)
    interesting.add(node.outs.most_common(2)[1][0])

  return interesting


def get_or_create(alias, employees_info):
  """Fetches an EmployeeInfo, or creates one if necessary."""

  employee_info = employees_info.get(alias)
  if employee_info is None:
    employees_info[alias] = info.Person(alias, alias, "")
  return employees_info[alias]


def get_aliases(filename):
  """Parse the aliases file, and extract an alias map.

  Returns a map from alias to list of emails, and a map from each email to
  alias."""

  aliases = {}
  inverse_aliases = {}

  with open(filename, "r") as f:
    lines = [line.strip() for line in f]

  for line in lines:
    parts = line.split(":")
    alias = parts[0].strip()
    emails = parts[1].split(",")
    emails = filter(bool, map(lambda x : x.strip(), emails))

    aliases[alias] = emails
    for email in emails:
      inverse_aliases[email] = alias

  return aliases, inverse_aliases


def should_remove(relation, remove_set):
  """Return true if a relation should be removed based on the remove_set."""

  return (relation.from_info in remove_set or
      relation.to_info in remove_set)


def parse_enron(relations, wiki_words):
  """Parse the enron.xml file, updating the relations list with relevant
  emails."""

  print "Parsing enron.xml"
  with open("data/enron.xml", "r") as f:
    line = f.readline()
    while len(line) > 0:
      line = line.strip()

      # Grab the message id, ignoring the one junk email in enron.xml.
      try:
        email = emails.Email(line.split()[1].split("/")[2], wiki_words)
      except IndexError:
        # Skip through the junk email.
        line = f.readline()
        while not re.match(r"^<DOC>", line) and len(line) > 0:
          line = f.readline()
        continue

      # Find the subject.
      line = f.readline()
      subject_match = re.match(r"^Subject: (.*)", line)
      while not subject_match and len(line) > 0:
        line = f.readline()
        subject_match = re.match(r"^Subject: (.*)", line)
      email.subject = subject_match.group(1) if subject_match else None

      # Find the start of the text body.
      line = f.readline()
      while line != "\n":
        line = f.readline()

      # Eat the text data.
      line = f.readline()
      while not re.match(r"^</DOC>", line):
        line.strip()
        email.add_line(line)
        line = f.readline()

      # Finally, add the email set to anyone who's involved.
      for relation in relations:
        if email.id in relation.from_info.node.outs_ids:
          relation.emails.add_email(email)

      # Move onto the next document.
      line = f.readline()


def get_relations(interesting_nodes, employees_info, wiki_words, n=4):
  """Find relations between the interesting nodes."""

 # Find which of the interesting nodes have sent each other emails.
  relations = set()
  for (from_node, to_node) in itertools.permutations(interesting_nodes, 2):
    # Note: node.email_address is an *alias* here.
    from_node_info = get_or_create(from_node.email_address, employees_info)
    to_node_info = get_or_create(to_node.email_address, employees_info)

    from_node_info.node = from_node
    to_node_info.node = to_node

    if from_node.outs[to_node] > n:
      relations.add(Relation(from_node_info, to_node_info))

  # Trim the relations list to remove single-neighbour nodes.
  relations = list(relations)
  changing = True
  while changing:
    changing = False

    tmp = collections.defaultdict(set)
    for relation in relations:
      tmp[relation.from_info].add(relation.to_info)
      tmp[relation.to_info].add(relation.from_info)

    to_remove = set()
    for (node, from_to_set) in tmp.iteritems():
      if len(from_to_set) < 2:
        to_remove.add(node)

    changing = len(to_remove) > 0

    relations[:] = (relation for relation in relations
        if not should_remove(relation, to_remove))

  # Parse enron.xml for interesting information about the pairs.
  parse_enron(relations, wiki_words)
  
  return relations


def get_wikipedia_words(filename):
  """Parse the wikipedia page for the words in it."""

  words = set()
  with open(filename, "r") as f:
    for line in f:
      line = line.strip()
      line = line.translate(string.maketrans("",""), string.punctuation)
      line_words = line.split()
      for word in line_words:
        word = word.lower()
        if word not in _stopwords:
          words.add(word)
  return words


def main():
  """Creates a graph.dot file with interesting information."""

  print "Parsing wikipedia.txt"
  wiki_words = get_wikipedia_words("data/wikipedia.txt")

  # Parse the aliases.txt file.
  print "Parsing aliases.txt"
  (aliases, inverse_aliases) = get_aliases("data/aliases.txt")

  # Parse the roles.txt file.
  print "Parsing roles.txt"
  employees_info = info.get_employees_map("data/roles.txt", inverse_aliases)

  # Parse the graph.txt file to get the email graph.
  print "Parsing graph.txt"
  (_, email_graph) = graphs.process_file("data/graph.txt", inverse_aliases)
  interesting_nodes = get_interesting_nodes(email_graph, aliases)

  relations = get_relations(interesting_nodes, employees_info, wiki_words)

  # Write the resultant graph.
  print "Writing results."
  with open("graph.dot", "w") as f:
    f.write('digraph G {\n')
    print "%s relations" % len(relations)
    for (i, relation) in enumerate(sorted(relations)):
      print "%s" % i
      a = relation.from_info
      b = relation.to_info

      # Choose the most common word in the email subjects.
      c = counter.Counter()
      for email in relation.emails.emails:
        if email.subject is not None:
          c.update(email.subject)
      if len(c) > 0:
        best_word = c.most_common(1)[0][0]
      else:
        best_word = ""

      f.write('"%s" -> "%s" [label = "%s"];\n' %
          (a.description(), b.description(), best_word))
    f.write('}\n')


if __name__ == "__main__":
  main()
