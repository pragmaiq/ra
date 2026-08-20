#
# pipeline settings and configuration options
#
import os

# an array of the files to be cleaned (swept)
SWEPT: list[str] = [sweep.strip() for sweep in os.getenv("SWEPT", "").split(",")]

# the output file after data being cleaned and swept
OUTPUT: str = "data/raw.jsonl"

# the default topic for unrecognized topics
TOPIC: str = "no-topic"

# the pill we provide to the queue to kill all the
# running workers, when they finish
POISON_PILL: str = "FREEZE"