import re


class Person(object):
  """Represents a person, with a name, alias, email address, and job."""
  
  def __init__(self, email, alias=None, extra=None):
    self.graph_node = None

    extra_parts = []
    if extra is not None:
      extra_parts = re.split(r" [ ]+", extra)
      extra_parts = filter(bool, extra_parts)

    self.alias = alias or email
    self.name = self._default_name(email)
    self.job = ""
    self.extra = ""

    try:
      # Grab the person's name, if specified.
      next = extra_parts.pop(0)
      if next == "xxx":
        raise IndexError
      self.name = next

      # Grab the person's job, if specified.
      next = extra_parts.pop(0)
      if next == "N/A":
        raise IndexError
      self.job = extra_parts.pop(0)

      # Grab any extra.
      self.extra = extra_parts.pop(0)
    except IndexError:
      # No more extra.
      pass

    # `Vice President' is overly wordy.
    self.job = self.job.replace("Vice President", "VP")
    self.extra = self.extra.replace("Vice President", "VP")

  def description(self):
    """Returns a text description of the person."""

    description = self.name

    if self.job == "Employee":
      # "Employee" is a useless description. Try to replace it with the
      # extra information, if there is any.
      if self.extra is not None:
        description += "\\n(%s)" % self.extra
    elif self.job is not None:
      if self.extra is not None and self.extra.startswith(self.job):
        # In this case we have something like "(VP, VP of X)", so discard
        # the first VP.
        description += "\\n(%s)" % self.extra
      else:
        # Otherwise create
        description += "\\n(%s" % self.job
        if self.extra is not None:
          description += ", %s" % self.extra
        description += ")"

    return description

  def _default_name(self, email):
    username = email.split("@")[0]
    name_parts = map(lambda x : x.title(), username.split('.'))
    return ' '.join(name_parts)


# The special cases dictionary captures places where the information from
# roles.txt should be overriden.
special_cases = {

  # pete.davis is an automated email generator.
  'pete.davis' : 'Broadcast Proxy'
}


def get_employees_map(roles_file, inverse_aliases):
  """Get a map from email addresses to Persons, based on the roles file."""
  
  with open(roles_file, "r") as f:
    lines = [line.strip() for line in f]

  employees_map = {}
  for line in lines:
    parts = line.split("\t")
    if len(parts) < 1:
      continue

    username = parts[0]
    # All the roles.txt files are Enron employees.
    email = username + "@enron.com"
    alias = inverse_aliases.get(email) or email

    if username in special_cases:
      extra = special_cases[username]
    else:
      extra = parts[1]
    employees_map[alias] = Person(email, alias, extra)

  return employees_map