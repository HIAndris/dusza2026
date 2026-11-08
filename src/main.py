import sys
from argparse import ArgumentError

from ide.ide import IDE

args = sys.argv[1:]

q_mode = False
if "-q" in args:
    q_mode = True
    args.remove("-q")

if len(args) != 2:
    raise ArgumentError(None, "Argumentumok: [-q] {input-txt} {output-txt}")

input_txt = args[0]
output_txt = args[1]

if not q_mode:
    ide = IDE(input_txt, output_txt)
    ide.main()
    sys.exit(0)

# todo
print("q mode")
sys.exit(0)