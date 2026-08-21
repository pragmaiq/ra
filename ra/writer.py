import json
import hashlib
from pathlib import Path
from multiprocessing import Queue

from ra.settings import OUTPUT, POISON_PILL, WORKERS

def _hash(text: str) -> str:
  return hashlib.md5(text.encode("utf-8")).hexdigest()

def writer_fn(clean_queue: Queue) -> dict:
  # main writer loop
  output_path = Path(OUTPUT)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  seen: set[str] = set()

  if output_path.exists():
    with open(output_path, encoding="utf-8") as f:
      for line in f:
        line = line.strip()
        if line:
          try:
            obj = json.loads(line)
            seen.add(_hash(obj.get("text", "")))
          except json.JSONDecodeError:
            continue

  written      = 0
  duplicates   = 0
  stats_received = 0
  worker_stats: list[dict] = []

  pills_needed = WORKERS
  with open(output_path, "a", encoding="utf-8") as f:
    while True:
      item = clean_queue.get()

      if isinstance(item, dict) and item.get("_stats"):
        worker_stats.append(item)
        stats_received += 1
        if stats_received >= pills_needed:
          break
        continue

      text_hash = _hash(item.get("text", ""))
      if text_hash in seen:
        duplicates += 1
        continue

      seen.add(text_hash)
      f.write(json.dumps(item, ensure_ascii=False) + "\n")
      written += 1

  return {
      "written": written,
      "duplicates": duplicates,
      "worker_stats": worker_stats,
  }