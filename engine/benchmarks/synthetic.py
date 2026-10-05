"""SyntheticDataGenerator: benchmark posts with planted near-duplicates
(plan, Sections 2.1.1 and 3).

Original captions are either taken from a list of real captions (base_captions)
or composed from category-specific sentence patterns (food, travel, fitness,
fashion, small business, personal). Captions in the same category share
vocabulary and closing lines, so unrelated posts overlap partially, as real ones do.

A planted duplicate is an earlier caption (possibly itself a copy) with controlled
edits: word deletion, insertion, swap and replacement, character typos, and
cosmetic changes that preprocessing should undo (case, emoji, hashtags, mentions,
links). The edit rate is drawn per copy, so planted pairs cover a range of
similarities. Every planted pair is returned with its edit count.

    python benchmarks/synthetic.py --n 300 --out ../data/sample/sample_posts.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ANY = {
    "adj": "amazing incredible unreal perfect cozy lovely wholesome chaotic peaceful underrated magical "
    "refreshing unforgettable humble simple delicious stunning wild beautiful surreal".split(),
    "when": "this weekend|tonight|tomorrow morning|next friday|this sunday|before the month ends|"
    "after work|on saturday".split("|"),
    "day": "monday|rainy evening|lazy sunday|long friday|quiet morning|busy tuesday|holiday".split("|"),
    "weather": "rainy|sunny|chilly|humid|breezy|foggy|stormy".split("|"),
    "people": "my sister|the whole family|my best friend|the squad|my parents|my roommates|"
    "my cousins|the team|my college gang".split("|"),
    "city": "Goa|Jaipur|Mumbai|Pune|Udaipur|Shimla|Rishikesh|Bengaluru|Kochi|Delhi|Manali|"
    "Pondicherry|Hampi|Darjeeling|Leh".split("|"),
    "feeling": "grateful|so happy|tired but happy|nostalgic|proud|blessed|recharged|motivated".split("|"),
}

CATEGORIES: dict[str, dict] = {
    "food": {
        "patterns": [
            "Tried the {dish} at {place} today and it was {adj}",
            "Homemade {dish} for {meal}, recipe coming soon",
            "Nothing beats {dish} on a {weather} {day}",
            "Our new {dish} is finally on the menu, come try it {when}",
            "Craving {dish} again, who is coming with me {when}",
            "Spent the afternoon learning to make {dish} with {people}",
            "Rate this {dish} out of ten, be honest",
            "First time trying {dish} in {city} and I am {feeling}",
        ],
        "dish": "butter chicken|masala dosa|pav bhaji|ramen|cold coffee|chocolate cake|paneer tikka|"
        "momos|biryani|filter coffee|sourdough bread|mango cheesecake|chole bhature|pasta arrabbiata|"
        "vada pav|tiramisu|hyderabadi haleem|matcha latte|pani puri|banana bread".split("|"),
        "place": "a tiny cafe near the station|the street stall outside college|our favourite dhaba|"
        "that rooftop place|a new bakery downtown|my grandmother's kitchen|the food court".split("|"),
        "meal": "breakfast|lunch|dinner|a midnight snack|sunday brunch|evening chai".split("|"),
    },
    "travel": {
        "patterns": [
            "Woke up to this view in {city} and still cannot believe it",
            "Three days in {city} with {people}, every moment was {adj}",
            "Chasing sunsets at {spot}, {feeling}",
            "Road trip to {city} done, next stop {city2}",
            "If you visit {city}, do not miss {spot}",
            "Packing light for {city} {when}, any recommendations",
            "Got lost in the lanes of {city} and found {spot}",
            "Missing the {weather} mornings at {spot}",
        ],
        "city2": ANY["city"],
        "spot": "the old fort|a hidden waterfall|the night market|the lake promenade|a hilltop temple|"
        "the backwaters|a quiet beach shack|the tea gardens|the sand dunes|the riverside ghats".split("|"),
    },
    "fitness": {
        "patterns": [
            "Day {num} of my {plan}, legs are done for",
            "New personal best on {lift} today, {feeling}",
            "Morning {activity} with {people} before the sun came up",
            "Consistency over intensity, showing up for {activity} again",
            "Rest day means {rest}, back stronger {when}",
            "Swapped my evening scroll for a {activity} session and feel {adj}",
            "Ran {num} kilometres in the {weather} weather today",
            "Small wins: {win}",
        ],
        "num": [str(i) for i in range(3, 61)],
        "plan": "75 day challenge|marathon prep|strength block|home workout plan|yoga streak|"
        "cutting phase|beginner running plan".split("|"),
        "lift": "deadlift|squat|bench press|pull ups|overhead press|plank hold".split("|"),
        "activity": "yoga|run|swim|cycling|hiit|pilates|badminton|climbing".split("|"),
        "rest": "stretching and a long nap|foam rolling and podcasts|a slow walk and good food".split("|"),
        "win": "drank three litres of water|slept eight hours|hit ten thousand steps|"
        "cooked every meal at home|stretched for twenty minutes".split("|"),
    },
    "fashion": {
        "patterns": [
            "Outfit of the day: {item} with {item2}, simple but {adj}",
            "Thrifted this {item} for almost nothing, cannot stop wearing it",
            "Styling one {item} three different ways, which one wins",
            "Wore my mother's {item} to {event} and got so many compliments",
            "{color} is my colour this season, fight me",
            "Getting ready for {event} with {people}",
            "Rewearing my favourite {item} because outfit repeating is cool",
            "Closet clean out done, kept only {item} and {item2}",
        ],
        "item": "linen shirt|silk saree|denim jacket|block print kurta|white sneakers|vintage blazer|"
        "oversized hoodie|jhumkas|leather boots|cotton dress|tie dye tee|handloom dupatta".split("|"),
        "item2": "gold hoops|cargo pants|a tote bag|kolhapuri chappals|a straw hat|round glasses|"
        "a messy bun|silver rings".split("|"),
        "event": "a friend's wedding|the college fest|a family dinner|diwali night|my cousin's sangeet|"
        "an office party|brunch".split("|"),
        "color": "Sage green|Terracotta|Mustard yellow|Navy blue|Lavender|Rust orange|Ivory".split("|"),
    },
    "business": {
        "patterns": [
            "Restocked: {product} is back in all sizes, order before it sells out",
            "Behind the scenes of packing {num} orders of {product} today",
            "Every {product} is handmade in our {workshop}, thank you for supporting small business",
            "Flat {num} percent off on {product} till {when}, link in bio",
            "Customer love: {review}",
            "Launching our {collection} collection {when}, set your reminders",
            "Meet the hands behind our {product}, the artisans from {city}",
            "Free shipping across India on {product} this week only",
        ],
        "num": [str(i) for i in range(10, 80, 5)],
        "product": "terracotta earrings|soy candles|block print tote bags|crochet tops|resin coasters|"
        "hand painted mugs|scented soaps|macrame plant hangers|brass diyas|beaded bracelets".split("|"),
        "workshop": "home studio|tiny workshop|garage studio|village workshop".split("|"),
        "review": "the quality is even better than the photos|arrived in two days and packed with love|"
        "my mother loved her gift|ordering a second one already".split("|"),
        "collection": "festive|monsoon|summer|wedding season|minimal|winter".split("|"),
    },
    "personal": {
        "patterns": [
            "Some days you just need {comfort} and {people}",
            "Throwback to {memory}, feels like yesterday",
            "Finally finished {task}, {feeling}",
            "Things that made me smile this week: {smile}",
            "Happy birthday to {people}, life is better with you around",
            "A {weather} {day}, {comfort} and an old playlist",
            "Reminder to be kind to yourself, especially on a {day}",
            "Quietly proud of {task}",
        ],
        "comfort": "a cup of chai|a good book|long walks|maggi at midnight|old bollywood songs|"
        "a warm blanket".split("|"),
        "memory": "our first trip together|graduation day|the summer we learnt to swim|"
        "school picnic days|the night we got stuck in the rain".split("|"),
        "task": "my semester exams|the painting I started in march|my first half marathon|"
        "moving into the new flat|my internship project|reading twenty books this year".split("|"),
        "smile": "street dogs napping in the sun|a handwritten letter|my plants finally flowering|"
        "a stranger's compliment|rain after a long summer".split("|"),
    },
}

# Optional openers and endings for each sentence; they multiply the number of distinct
# sentences so that unrelated captions rarely share a whole sentence by chance.
OPENERS = (
    "Honestly,|Okay so|Not gonna lie,|Update:|Quick one:|Real talk,|Plot twist:|Fun fact:|PSA:|"
    "Low key,|Ngl,|Story time:|Okay but|Lately,|Today,|Finally,|Guess what,|Sunday thoughts:|Hot take:|"
    "Can confirm,|So yes,|Little update:|Proof that|Again,|For the record,"
).split("|")
ENDINGS = (
    "and I loved every second|no regrets|would do it again|ten out of ten|low key obsessed|send help|"
    "as always|for the third time this month|with zero plans|and it was worth it|no filter needed|"
    "right before the rain|on a whim|with a playlist on loop|and I am not okay|still smiling|"
    "with my phone on silent|after a long week|which nobody expected|like old times|thanks to you all|"
    "for the very first time|at 6 am|on a budget|without any planning|and the photos do not do it justice|"
    "while the city slept|all thanks to my mom|in record time|and yes it rained"
).split("|")

CLOSERS = (
    "What do you think?|Tag someone who needs this.|Save this for later.|Link in bio.|"
    "Thank you for the love.|More soon.|Drop a heart if you agree.|Share with your friends.|"
    "Let me know in the comments.|Stay tuned."
).split("|")

TAGS = {
    "food": "#food #foodie #homemade #instafood #streetfood #foodblogger #yummy #desifood".split(),
    "travel": "#travel #wanderlust #incredibleindia #travelgram #roadtrip #explore #mountains #beach".split(),
    "fitness": "#fitness #workout #gym #running #yoga #fitnessmotivation #healthylifestyle".split(),
    "fashion": "#ootd #fashion #style #thrift #sustainablefashion #outfitinspo #ethnicwear".split(),
    "business": "#smallbusiness #handmade #shopsmall #supportlocal #madeinindia #newcollection".split(),
    "personal": "#life #memories #grateful #mood #weekend #throwback #selflove".split(),
}
COMMON_TAGS = "#instagood #photooftheday #reels #explorepage #love".split()
EMOJI = "🔥 ✨ ❤️ 😍 🙌 😂 🌸 ☕ 🌊 💪 🛍️ 🙏".split()


@dataclass(frozen=True)
class PlantedPair:
    source: int  # index of the caption that was copied
    copy: int  # index of the edited copy
    n_edits: int  # word/character edits (cosmetic changes not counted)


@dataclass
class SyntheticSet:
    captions: list[str]
    categories: list[str]
    planted: list[PlantedPair]

    @property
    def planted_pairs(self) -> list[tuple[int, int]]:
        return [(p.source, p.copy) for p in self.planted]


class SyntheticDataGenerator:
    def __init__(self, seed: int = 42, base_captions: list[str] | None = None) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.base_captions = list(base_captions or [])

    # ---- captions -------------------------------------------------------------

    def _fill(self, pattern: str, cat: dict) -> str:
        out = pattern
        while "{" in out:
            start = out.index("{")
            end = out.index("}", start)
            slot = out[start + 1 : end]
            out = out[:start] + self.rng.choice(cat.get(slot) or ANY[slot]) + out[end + 1 :]
        return out

    def compose_caption(self, category: str | None = None) -> tuple[str, str]:
        """A new original caption and its category."""
        category = category or self.rng.choice(list(CATEGORIES))
        cat = CATEGORIES[category]
        sentences = []
        for pattern in self.rng.sample(cat["patterns"], self.rng.choice((2, 3, 3))):
            sentence = self._fill(pattern, cat)
            if self.rng.random() < 0.5:
                sentence = self.rng.choice(OPENERS) + " " + sentence[0].lower() + sentence[1:]
            if self.rng.random() < 0.5:
                sentence += " " + self.rng.choice(ENDINGS)
            sentences.append(sentence)
        text = ". ".join(sentences) + "."
        if self.rng.random() < 0.6:
            text += " " + self.rng.choice(CLOSERS)
        return self._decorate(text, category), category

    def _decorate(self, text: str, category: str) -> str:
        rng = self.rng
        if rng.random() < 0.5:
            text += " " + "".join(rng.sample(EMOJI, rng.randint(1, 3)))
        if rng.random() < 0.15:
            text += " @" + rng.choice(["mom", "bestie", "the.studio", "chef_ankit", "travelwithriya"])
        if rng.random() < 0.05:
            text += " https://shop.example.in/p/" + str(rng.randint(100, 999))
        if rng.random() < 0.8:
            tags = rng.sample(TAGS[category], rng.randint(1, 5)) + rng.sample(COMMON_TAGS, rng.randint(0, 2))
            text += "\n\n" + " ".join(tags)
        return text

    # ---- edits ----------------------------------------------------------------

    def edit_caption(self, caption: str, category: str, edit_rate: float) -> tuple[str, int]:
        """Copy with about edit_rate * (number of words) edits, plus cosmetic changes."""
        rng = self.rng
        body, _, _tags = caption.partition("\n\n")
        words = [w for w in body.split() if not w.startswith(("#", "@", "http")) and not _is_emoji(w)]
        n_edits = round(edit_rate * len(words))
        vocab = [w for p in CATEGORIES[category]["patterns"] for w in p.split() if "{" not in w]
        for _ in range(n_edits):
            op = rng.choice(("delete", "insert", "swap", "replace", "typo"))
            i = rng.randrange(len(words))
            if op == "delete" and len(words) > 4:
                words.pop(i)
            elif op == "insert":
                words.insert(i, rng.choice(vocab))
            elif op == "swap" and len(words) > 1:
                j = min(i + 1, len(words) - 1)
                words[i], words[j] = words[j], words[i]
            elif op == "replace":
                words[i] = rng.choice(vocab)
            else:
                w = words[i]
                if len(w) > 3:
                    k = rng.randrange(len(w))
                    words[i] = w[:k] + rng.choice("aeiourstnl") + w[k + 1 :]
        text = " ".join(words)
        # Cosmetic changes the preprocessor removes: case, emoji, mentions, links, hashtags.
        if rng.random() < 0.3:
            text = text.upper() if rng.random() < 0.2 else text.capitalize()
        return self._decorate(text, category), n_edits

    # ---- data sets ------------------------------------------------------------

    def generate(self, n: int, dup_fraction: float = 0.15, max_edit_rate: float = 0.3) -> SyntheticSet:
        """n captions; about dup_fraction of them are edited copies of earlier captions.

        Each copy's edit rate is drawn uniformly from [0, max_edit_rate].
        """
        rng = self.rng
        captions: list[str] = []
        categories: list[str] = []
        planted: list[PlantedPair] = []
        base = list(self.base_captions)
        seen: set[str] = set()
        rng.shuffle(base)
        for i in range(n):
            if captions and rng.random() < dup_fraction:
                src = rng.randrange(len(captions))
                text, n_edits = self.edit_caption(captions[src], categories[src], rng.uniform(0, max_edit_rate))
                captions.append(text)
                categories.append(categories[src])
                planted.append(PlantedPair(src, i, n_edits))
            else:
                if base:
                    captions.append(base.pop())
                    categories.append("personal")  # vocabulary used for edits of real captions
                else:
                    while True:  # originals must differ from each other in their wording
                        text, cat = self.compose_caption()
                        key = text.partition("\n\n")[0].lower()
                        if key not in seen:
                            seen.add(key)
                            break
                    captions.append(text)
                    categories.append(cat)
        return SyntheticSet(captions, categories, planted)

    def generate_posts(self, n: int, n_accounts: int = 12, **kwargs) -> tuple[list[dict], SyntheticSet]:
        """Posts with the fields of the posts table (plan, Section 5.4), ready for CSV.

        Engagement scales with the account's follower count, with a per-category
        effect and log-normal noise, so Module 2 has a signal to rank.
        """
        rng = self.rng
        data = self.generate(n, **kwargs)
        followers = [int(math.exp(rng.uniform(math.log(500), math.log(200_000)))) for _ in range(n_accounts)]
        cat_effect = {c: rng.uniform(0.6, 1.6) for c in CATEGORIES}
        start = datetime(2024, 1, 1)
        posts = []
        for i, (caption, cat) in enumerate(zip(data.captions, data.categories)):
            acc = rng.randrange(n_accounts)
            rate = 0.04 * cat_effect.get(cat, 1.0) * math.exp(rng.gauss(0, 0.6))
            likes = int(followers[acc] * rate)
            posts.append(
                {
                    "id": f"p{i:05d}",
                    "account": f"acc_{acc:02d}",
                    "caption": caption,
                    "timestamp": (start + timedelta(minutes=rng.randrange(2 * 365 * 24 * 60))).isoformat(),
                    "likes": likes,
                    "comments": int(likes * rng.uniform(0.01, 0.06)),
                    "followers": followers[acc],
                }
            )
        return posts, data


def _is_emoji(word: str) -> bool:
    return all(ord(ch) > 0x2000 for ch in word)


def read_captions(path: Path) -> list[str]:
    """Captions from a CSV with a 'caption' column, or one caption per line of a text file."""
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            return [row["caption"] for row in csv.DictReader(f) if row.get("caption")]
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    p = argparse.ArgumentParser(description="Write synthetic posts to CSV.")
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--accounts", type=int, default=12)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    posts, data = SyntheticDataGenerator(args.seed).generate_posts(args.n, n_accounts=args.accounts)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(posts[0]))
        writer.writeheader()
        writer.writerows(posts)
    print(f"wrote {len(posts)} posts ({len(data.planted)} planted duplicates) to {args.out}")


if __name__ == "__main__":
    main()
