#
# pipeline settings and configuration options
#
import os
 
# a list of .jsonl files to process
SWEPT: list[str] = [s.strip() for s in os.getenv("SWEPT", "").split(",") if s.strip()]
 
# output file path
OUTPUT: str = os.getenv("OUTPUT", "data/raw.jsonl")
 
# default topic when flair is null/empty
TOPIC: str = "general"
 
# number of worker processes
WORKERS: int = int(os.getenv("WORKERS", "4"))
 
# poison pill — sent to workers when all input is exhausted
POISON_PILL: str = "FREEZE"
 
# score thresholds
MIN_POST_SCORE: int = int(os.getenv("MIN_POST_SCORE", "2"))
MIN_COMMENT_SCORE: int = int(os.getenv("MIN_COMMENT_SCORE", "1"))
 
# minimum arabic character ratio (0.0 - 1.0)
MIN_ARABIC_RATIO: float = float(os.getenv("MIN_ARABIC_RATIO", "0.4"))