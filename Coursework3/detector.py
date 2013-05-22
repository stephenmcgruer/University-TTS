import counter
import itertools 
import optparse
import speeches


def output(matching_tuples, filename):
  """Outputs a set of matches to a file.

  Can accept matches as either a list of 2-tuples, or as a list of iterables
  of matching elements. In the latter case, will enumerate all pairs from the
  sublists, with order-equality (i.e. (a, b) == (b, a)).

  Examples:
    output([[a, b], [a, c], [c, b], [d, e]], filename)
      Writes the following to filename:
        a-b
        a-c
        b-c
        d-e

    output([[a, b, c], [d, e]], filename)
      Writes the following to filename:
        a-b
        a-c
        b-c
        d-e
  """

  # In order to retain the same order for any approach, sort the matches.
  ordered_matches = []
  for matches in matching_tuples:
    # In the case where matching_tupels are pairs anyway, this is a no-op.
    pairs = itertools.combinations(matches, 2)
    ordered_matches.extend(pairs)
  ordered_matches.sort(key=lambda (a, b) : min(int(a), int(b)))

  # Now write them to a file, smallest pair element first.
  with open(filename, "w") as f:
    for (a, b) in ordered_matches:
      if int(a) < int(b):
        f.write("%s-%s\n" % (a, b))
      else:
        f.write("%s-%s\n" % (b, a))


def exact_detection(speech_set, use_exact_overlap):
  """Performs exact duplicate detection.

  If the parameter use_exact_overlap is set, a brute force, exact equality
  comparison will be performed. Otherwise, a fingerprint-based inverted index
  will be used to quickly find duplicates. Note that the fingerprint is not
  guaranteed to be unique, so there may be some (but statistically very few)
  false positives."""

  if use_exact_overlap:
    # No fingerprint - brute force compare all documents.
    pairs = itertools.combinations(speech_set.speeches, 2)
    filtered_pairs = [(a.id, b.id) for (a, b) in pairs if a.tokens == b.tokens]
    overlapping_speeches = set(filtered_pairs)
  else:  
    # Use the inverted index for the "exact" hashes provided by the speech set.
    overlapping_speeches = set()
    for overlaps in speech_set.exact_fingerprints.values():
      if len(overlaps) > 1:
        overlapping_ids = tuple([overlap.id for overlap in overlaps])
        overlapping_speeches.add(overlapping_ids)

  return overlapping_speeches


def hamming_distance(number1, number2):
  """Calculate the Hamming distance between two binary numbers.

  The numbers can be given as any iterable."""

  pairs = zip(number1, number2)
  non_equal_pairs = filter(lambda (a, b) : a != b, pairs)

  return len(non_equal_pairs)


def near_detection(speech_set, use_groups, similarity_distance):
  """Performs near duplicate detection.

  The similarity_distance variable sets the distance to accept matches at. If
  use_groups is set, then this is the maximum number of non-matching groups for
  two speeches to be found equal. Otherwise, it's the maximum Hamming distance
  between two speeches for them to be found equal."""

  overlapping_speeches = set()
  if use_groups:
    # To do a L-groups-of-k-bits overlap detection, iterate over every speech
    # and look for other speeches who are in a large number of the same
    # buckets. O(nd), where d is the maximimum number of documents in any
    # bucket of any group.

    for speech in speech_set.speeches:
      number_buckets = len(speech.near_fingerprint_buckets)

      match_counter = counter.Counter()
      for bucket in speech.near_fingerprint_buckets:
        match_counter.update(bucket)

      for (match, count) in match_counter.most_common():
        # Don't want to match ourself!
        if speech == match:
          continue

        if (number_buckets - count) > similarity_distance:
          # No more matches will be close enough.
          break

        # Order the pair to avoid duplicates.
        if speech.id < match.id:
          overlapping_speeches.add((speech.id, match.id))
        else:
          overlapping_speeches.add((match.id, speech.id))
  else:
    # Brute force search of the speeches.
    pairs = itertools.combinations(speech_set.speeches, 2)
    for (a, b) in pairs:
      distance = hamming_distance(a.near_fingerprint, b.near_fingerprint)
      if distance <= similarity_distance:
        overlapping_speeches.add((a.id, b.id))

  return overlapping_speeches


def finn_detection(speech_set, use_groups, similarity_distance):
  """Performs a finn duplicate detection.

  The finn duplicate detection operates across plateaus in the texts,
  comparing a near-fingerprint for each to other documents plateaus.

  The similarity_distance variable sets the distance to accept matches at. If
  use_groups is set, then this is the maximum number of non-matching groups for
  two plateaus to be found equal. Otherwise, it's the maximum Hamming distance
  between two plateaus for them to be found equal."""

  overlapping_speeches = set()

  if use_groups:
    # To do a L-groups-of-k-bits overlap detection, iterate over every speech
    # and look for other speeches who are in a large number of the same
    # buckets. O(nd), where d is the maximimum number of plateaus in any
    # bucket of any group.

    for speech in speech_set.speeches:
      # Skip speeches without plateaus.
      if speech.plateau_fingerprint is None:
        continue

      number_buckets = len(speech.near_fingerprint_buckets)

      match_counter = counter.Counter()
      for bucket in speech.plateau_fingerprint_buckets:
        match_counter.update(bucket)

      for (match, count) in match_counter.most_common():
        # Don't want to match ourself!
        if speech == match:
          continue

        if (number_buckets - count) > similarity_distance:
          # No more matches will be close enough.
          break

        # Order the pair to avoid duplicates.
        if speech.id < match.id:
          overlapping_speeches.add((speech.id, match.id))
        else:
          overlapping_speeches.add((match.id, speech.id))
  else:
    # Brute force search of the plateaus.
    pairs = itertools.combinations(speech_set.speeches, 2)
    for (a, b) in pairs:
      if a.plateau_fingerprint is None or b.plateau_fingerprint is None:
        continue

      distance = hamming_distance(a.plateau_fingerprint, b.plateau_fingerprint)
      if distance <= similarity_distance:
        overlapping_speeches.add((a.id, b.id))

  return overlapping_speeches


def main():
  parser = optparse.OptionParser()
  parser.add_option("-e", "--exact",
      action="store_true",
      default=False,
      dest="use_exact_overlap",
      help="Do full overlap matching for exact-duplicate detection.")
  parser.add_option("-t", "--training",
      action="store_true",
      default=False,
      dest="use_training_data",
      help="Use the training data instead of the real data.")
  parser.add_option("--no-zlib",
      action="store_false",
      # Note that by default the variable 'use_zlib' is *true* - that is,
      # default to using zlib!
      default=True,
      dest="use_zlib",
      help="Do not use zlib for the exact checksum calculation.")
  parser.add_option("-s", "--similarity_distance",
      action="store",
      type="int",
      default=4,
      dest="similarity_distance",
      metavar="DISTANCE",
      help="The maximum distance allowed between two documents for them to be "
           "considered equal. If no-groups is set, this is the maximum "
           "Hamming distance, else it is the maximum number of divergent "
           "groups between the two documents.")
  parser.add_option("-b", "--bit_size",
      action="store",
      type="int",
      default=128,
      dest="bit_size",
      metavar="SIZE",
      help="The bit size used in the simhash generation.")
  parser.add_option("--no-groups",
      action="store_false",
      # Note that by default the variable 'use_groups' is *true* - that is,
      # default to using groups!
      default=True,
      dest="use_groups",
      help="Do not use L groups of k bits for near duplicate detection.")

  (options, _) = parser.parse_args()

  folder_name = "data"
  if options.use_training_data:
    folder_name = "train"

  print "Processing speeches from the %s directory." % folder_name
  the_speeches = speeches.SpeechSet(
      folder_name,
      use_zlib=options.use_zlib,
      bit_size=options.bit_size,
      use_groups=options.use_groups)

  print "Checking for exact duplication."
  exact_matches = exact_detection(the_speeches, options.use_exact_overlap)
  output(exact_matches, "exact.txt")

  print "Checking for near duplication."
  near_matches = near_detection(the_speeches, options.use_groups,
      options.similarity_distance)
  output(near_matches, "near.txt")

  print "Checking for near duplication in plateaus."
  finn_matches = finn_detection(the_speeches, options.use_groups,
      options.similarity_distance)
  output(finn_matches, "finn.txt")

  print "Done!"


if __name__ == "__main__":
  main()