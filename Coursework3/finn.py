def find_plateau(words, inverse_slope=100):
  """Returns the largest plateau in the given text.

  Non-numbers are treated as 'tags' within the document, while numbers are the
  tokens."""

  x_vector = [_convert_word(word) for word in words]

  # There is no point continuing if there are no tokens.
  if sum(x_vector) == len(x_vector):
    return None

  # Analyze X for useful information.
  (runs, words_before, tags_before, tags_after) = _get_info(x_vector)

  # The best plateau starts as the entire document.
  best_score = 0
  best_a = 0
  best_b = len(runs) - 1

  for (a, run_a) in _enum(runs, end=len(runs) -1):
    # There is never any reason to start in tag space.
    if run_a > 0:
      continue

    for (b, run_b) in _enum(runs, start=a, end=len(runs) - 1):
      # Nor any reason to end in tag space.
      if run_b > 0:
        continue

      # Calculate the number of tokens between a and b, aka
      # sum_{i=a}^{b} (1 - x_i).
      tokens_before_a = words_before[a] - tags_before[a]
      tokens_before_b = words_before[b] - tags_before[b]
      tokens_between = tokens_before_b - tokens_before_a

      # Calculate the total score.
      score = tags_before[a] + inverse_slope * tokens_between + tags_after[b]

      if score > best_score:
        best_score = score
        best_a = a
        best_b = b

  # The starting index is the total number of words that occured before
  # best_a, and similarly for the ending index.
  starting_index = words_before[best_a] - 1
  ending_index = words_before[best_b]

  plateau_words = words[starting_index:ending_index]

  # The plateau should have a reasonable amount of numbers.
  if len(filter(_is_token, plateau_words)) < 3:
    return None

  return plateau_words


def _convert_word(word):
  """Returns the X vector value for a word - 1 if it is a tag, 0 elsewise."""

  return 1 if _is_tag(word) else 0


def _is_tag(word):
  """Determines if a word is a 'tag', i.e. if it is not a number."""

  return not _is_token(word)


def _is_token(word):
  """Determines if a word is a 'token', i.e. if it is a number."""

  # Any string representation of a number can be cast to a float. If the cast
  # fails, it's not a number.
  try :
    float(word)
  except ValueError:
    return False

  return True


def _get_info(x_vector):
  """Calculates the necessary information to find plateaus in O(n^2).

  The first step is to compress the x_vector. It's clear that only 'runs' of
  tags/tokens are interesting, because we would never start or stop our
  plateau half-way through a run (for a tag run, we either want to start after
  it, stop before it, or stop at the end of the tokens that follow. Similarly
  for a token run, why stop halfway?) So first these runs are calculated,
  along with the total count of words at each run start.

  The tags_before and tags_after arrays are equivalent to sum_{i = 1}^{a} x_i
  and sum_{i = b + 1}^{n} x_i respectively, at all interesting values of (a,
  b) - i.e. at the start/end of runs."""

  # First, calculate the runs of tags/tokens in the data, and the
  # number of words at each run start.
  runs = [x_vector[0]] 
  words_before = [1]
  i = 0
  for digit in x_vector[1:]:
    if _run_changed(runs[i], digit):
      # New run.
      runs.append(0)
      words_before.append(words_before[-1])
      i += 1
    runs[i] += digit
    words_before[i] += 1

  # Then calculate the number of tags before any particular run.
  tags_before = [0]
  tags = 0
  for run in runs:
    if run > 0:
      tags += run
    tags_before.append(tags)

  # Finally, the number of tags after any particular run. 
  # It's a lot faster to do two reverses than it is to insert on the front.
  tags_after = [0]
  tags = 0
  for run in reversed(runs):
    if run > 0:
      tags += run
    tags_after.append(tags)
  tags_after.reverse()

  return runs, words_before, tags_before, tags_after


def _run_changed(run, digit):
  """Determine if a new run is starting."""

  if run == 0:
    return digit == 1
  else:
    return digit == 0


def _enum(seq, start=0, end=-1):
  """Version of enumerate that handles start/end indices."""

  if end < 0:
    end = len(seq)
  for (i, element) in enumerate(seq[start:]):
    adjusted_index = i + start
    if adjusted_index >= end:
      return
    yield (adjusted_index, element)