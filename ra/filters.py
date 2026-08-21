import re

IRAQI_MARKERS: list[str] = [
  "شكو ماكو", "شكو", "ماكو", "أكو",
  "لعد", "چا", "هسة", "هسه",
  "شلونك", "شلونچ", "شلونج", "شگد", "شكد",
  "هيج", "هيچ", "ياخويا", "يمعود", "يمعودة", "عيني",
  "صدگ", "صدك", "عبالي", "بلكت", "فد", "خوش", "كلش",
  "باوع", "تباوع", "يندل", "أندل",
  "طفر", "يطفر", "يطب", "طب",
  "دير بالك", "عوف", "عوفه",
  "سديت", "سده", "دا",
  "هواية", "هوايه", "باجر", "باچر",
  "خطية", "ختية", "فدوة", "فدوه",
  "دربونة", "دربونه", "خاشوكة", "خاشوگه",
  "چطل", "جطل", "ميز", "قنفة",
  "صوندة", "صونده", "بنكة", "بنكه",
  "جام", "بطانية", "بطانيه", "ياخويه", "ياخي"
]

# bad dialect markers, words/slangs from other dialects
BAD_MARKERS: set[str] = {
  "دلوقتي", "عشان", "ازيك", "كده", "بتاع", "بتاعتي", "إزاي",
  "بص", "فين", "مين", "امبارح", "بكره", "يسطا", "بجد",
  "معلش", "خالص", "برضه", "عامل ايه", "ياعم", "جوا", "برا",
  "هيك", "بدي", "بدك", "شو", "عم", "مشان", "هلق",
  "زلمة", "بركي", "قديش", "هاد", "هيدا", "كتير", "منيح",
  "بكرة",
  "بزاف", "واخا", "دابا", "ديالي", "ديالك", "واش", "برشا",
  "يزي", "شنوة", "هدرة", "كيداير", "مليح", "زوين",
  "خايب", "كنبغيك", "باهي", "علاش", "فاش", "هكا",
  "وايد", "أبي", "تكفى", "وش", "ايش", "ابشر",
    "مره", "طال عمرك", "ريال", "دريشة", "وشو",
  "زول", "داير", "اسي", "سمح", "ياخ",
}

def clean(text: str) -> str:
  #
  # normalizes input text, removes:
  # tatweel (مـــرحـــبـــا ===> مرحبا)
  # repeated chars: (مررررحبا ===> مررحبا)
  #
  text = re.sub(r"ـ+", "", text)
  text = re.sub(r"(.)\1{2,}", r"\1\1", text)
  return text.strip()


def arabic_ratio(text: str) -> float:
  # the fraction of characters that are arabic
  if not text:
      return 0.0
  arabic = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
  return arabic / len(text)

def has_bad_markers(text: str) -> bool:
  words = set(text.split())
  return bool(words & BAD_MARKERS)

def has_iraqi_markers(text: str) -> bool:
  return any(marker in text for marker in IRAQI_MARKERS)

def is_acceptable(
  text: str,
  score: int = 0,
  is_comment: bool = False,
  min_arabic_ratio: float = 0.4,
) -> tuple[bool, str]:
  #
  # runs all the quality filters on the input text
  #

  # 0 upvote's for a comment, I guess 0 is a good choice,
  # cuz not always a comment has a lot of upvote's, we care
  # more about the length of the comment
  min_score = 0 if is_comment else 2
  if score < min_score:
      return False, "low_score"

  if text in ("[deleted]", "[removed]", ""):
      return False, "deleted"

  if len(text) < 30:
      return False, "too_short"

  if arabic_ratio(text) < min_arabic_ratio:
      return False, "not_arabic"

  if has_bad_markers(text):
      return False, "bad_dialect"

  return True, "ok"