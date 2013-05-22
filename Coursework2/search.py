import best
import errno
import os
import re
import subprocess
import multiprocessing

# Naughty to do this, but it's a one-off script.
truth_rel = "truth.rel"
query_file = "data/qrys.txt"
data_file = "data/docs.txt"
regex = "[ ]{9}([01]\.[0-9]{4})"
search_dir = "search"


def run_a_search(k, results):
  k = float(k) / 10
  for n_d in xrange(15, 31):
    n_w_base = (n_d * 2) - 10
    n_w_ceiling = (n_d * 2) + 10
    for n_w in xrange(n_w_base, n_w_ceiling):
      print "Trying (k = %s, n_d = %s, n_w = %s)..." % (k, n_d, n_w)
      file = "%s_%s_%s.top" % (k, n_d, n_w)
      output_path = os.path.join(search_dir, file)

      prf = best.PseudoRelevanceFeedback(k, n_d, n_w)
      prf.calculate_similarity(query_file, data_file, output_path)

      text = subprocess.Popen(["./trec_eval", "-o", "-c", "-M1000",
          truth_rel, output_path], stdout=subprocess.PIPE).stdout.read()
      value = float(re.search(regex, text).group(1))
      results.append((k, n_d, n_w, value))

      os.remove(output_path)


def run_search():
  threads = []
  results = []
  for k in xrange(1, 31):
    run_a_search(k, results)

  csv_filename = "search.csv"
  with open(csv_filename, "w") as f:
    old_doc = 0
    for result in results:
      if result[0] != old_doc:
        f.write("\n")
        old_doc = result[0]
      f.write(",".join(map (str, result)))
      f.write("\n")

def main():
  # Make the directory if it doesnt exist.
  try:
    os.mkdir(search_dir)
  except OSError as exc:
    if exc.errno != errno.EEXIST:
      raise
  
  run_search()
    
if __name__ == "__main__":
  main()
