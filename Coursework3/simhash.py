import hashlib
from nltk.corpus import stopwords
import warnings


# The DICE version of nltk is old and has a deprecation warning. Ignore it.
with warnings.catch_warnings():
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  _stopwords = set(stopwords.words('english'))


def hash(token_counter, bit_size):
  """Compute the simhash of the tokens in token_counter.

  If given, bit size must be a power of 2."""

  # Check that bit_size is a power of 2.
  if not(_is_power_of_two(bit_size)):
    raise ValueError("bit_size is not a power of 2!")

  hashed_tokens = [_simhash_binary_md5(token, token_counter, bit_size)
      for token in token_counter if token not in _stopwords]

  summed_columns = [sum(x) for x in zip(*hashed_tokens)]
  simhash = [1 if column > 0 else 0 for column in summed_columns]

  return simhash


def _simhash_binary_md5(token, token_counter, bit_size):
  """Returns the sim-hash binary version of a md5 hash of an input token.

  This is created by hashing with md5, converting to binary, replacing all
  '0's with '-1', and multiplying through by token_counter.

  The hash is truncuated to bit_size bits. Truncuating to less than 128 will
  cause an increase in collisions, but so would using a smaller hash! If
  bit_size is greater than 128, it will be ignored.

  The returned value is a list of integers."""

  hashed_word = hashlib.md5(token)
  hex_digest = hashed_word.hexdigest()[:bit_size / 4]
  binary_string = bin(int(hex_digest, base=16))

  # Slice off the '0b'.
  binary_string = binary_string[2:]

  # Create a list version of the string, replacing 0 with -1
  # and multiplying through.
  frequency = token_counter[token]
  binary_list = [0] * (bit_size - len(binary_string))
  for character in binary_string:
    value = int(character)
    if value == 0:
      value = -1
    value *= frequency

    binary_list.append(value)

  return binary_list


def _is_power_of_two(number):
  """Checks if a number is a power of 2."""

  return number > 0 and ((number & (number - 1)) == 0)