import json

from multiprocessing import Queue
from multiprocessing.managers import SyncManager

from ra.filters import clean, is_acceptable
from ra.settings import MIN_ARABIC_RATIO, POISON_PILL, TOPIC

def _extract(raw: dict) -> tuple[str, str, str, int, bool] | None:
  #
  # extracts the fields we need from the raw reddit object
  # all we need is `subreddit`, `flair`, `text`, `score`,
  # and `is_comment`
  #
  # post ===> {title}\n{selftext}
  # comment ===> {body}
  #

  subreddit = raw.get("subreddit", "")
  if not subreddit:
    return None

  score = int(raw.get("score", 0))
  flair = (raw.get("link_flair_text") or "").strip()

  if "selftext" in raw:
    # a post
    title    = (raw.get("title") or "").strip()
    selftext = (raw.get("selftext") or "").strip()

    if selftext in ("[deleted]", "[removed]", ""):
      # it's okay if the post is without a body, we
      # will use the title only, if long enough
      text = title
    else:
      text = f"{title}\n{selftext}" if title else selftext

    return subreddit, flair, text, score, False

  elif "body" in raw:
    # a comment
    body = (raw.get("body") or "").strip()
    return subreddit, flair, body, score, True

  return None


def worker_fn(
  raw_queue: Queue,
  clean_queue: Queue,
  worker_id: int,
) -> None:
  #
  # main worker loop, keeps running until receiving
  # `POISON_PILL` from the queue
  #
  processed = 0
  accepted  = 0
  rejected: dict[str, int] = {}

  while True:
    item = raw_queue.get()
    if item == POISON_PILL:
      clean_queue.put({
        "_stats": True,
        "worker_id": worker_id,
        "processed": processed,
        "accepted": accepted,
        "rejected": rejected,
      })
      break

    line, filename = item
    try:
      raw = json.loads(line)
    except (json.JSONDecodeError, ValueError):
      rejected["invalid_json"] = rejected.get("invalid_json", 0) + 1
      processed += 1
      continue

    extracted = _extract(raw)
    if extracted is None:
      rejected["no_fields"] = rejected.get("no_fields", 0) + 1
      processed += 1
      continue

    subreddit, flair, text, score, is_comment = extracted

    # Clean text before filtering
    text = clean(text)

    # Run quality filters
    ok, reason = is_acceptable(
      text,
      score=score,
      is_comment=is_comment,
      min_arabic_ratio=MIN_ARABIC_RATIO,
    )

    if not ok:
      rejected[reason] = rejected.get(reason, 0) + 1
      processed += 1
      continue

    entry = {
      "source": f"reddit/r/{subreddit}",
      "topics": flair,
      "text": text,
    }

    clean_queue.put(entry)
    accepted += 1
    processed += 1