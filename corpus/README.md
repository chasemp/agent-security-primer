# Camp Letters Corpus

Training data for Pillar 1 demos. 1000 synthetic letters home from
summer camp, written in the voice of kids aged 8-12.

## Structure

Individual letters live in `camp_letters.d/`, organized by category:

```
camp_letters.d/
├── arrival/          First days: nervous, describing the place, new bunkmates
├── homesick/         Missing family, pets, own bed, wanting comfort
├── adventure/        Activities: kayaking, hiking, campfire, ropes course
├── friendship/       New friends, group dynamics, inside jokes
├── food/             Mess hall highs and lows, care package requests
├── rainy_day/        Stuck inside, board games, cabin fever, boredom
├── growth/           Learned something, conquered a fear, helped someone
├── last_days/        Counting down, mixed feelings, promises to stay in touch
```

Each letter is a standalone `.txt` file, 50-150 words.

## Categories

Eight categories, ~125 letters each. Categories overlap intentionally —
a "friendship" letter might mention food, an "adventure" letter might
mention a friend. The primary category reflects the dominant theme.

| Category | Count | Dominant Pattern |
|----------|-------|-----------------|
| arrival | ~125 | "Dear Mom/Dad, I got here and..." |
| homesick | ~125 | "I miss...", "Can you send...", "When is pickup..." |
| adventure | ~125 | "Today we went...", "You won't believe...", excited tone |
| friendship | ~125 | "My new friend...", "We all...", names and nicknames |
| food | ~125 | "The food here is...", "Please send...", mess hall stories |
| rainy_day | ~125 | "It rained all day...", "We had to stay inside...", bored tone |
| growth | ~125 | "I finally...", "I was scared but...", proud tone |
| last_days | ~125 | "Only X days left...", "I'm going to miss...", reflective tone |

## Why These Categories

For training demos: each category has distinct vocabulary and sentiment
patterns. A bigram model will learn different distributions for each.

For RL demos: you can reward specific themes. "Reward letters that
mention making friends" will shift output toward friendship-category
patterns. "Reward letters that mention trying something new" shifts
toward growth/adventure. The audience sees the reward signal reshape
which patterns the model prefers.

For golden dataset demos (Pillar 3): the categories provide natural
evaluation dimensions. "Classify this letter's mood" or "Is this an
arrival letter or a last-days letter?" become eval tasks.

## Building the Training File

```bash
python corpus/build_corpus.py
```

Produces `corpus/camp_letters.txt` — all letters concatenated with
`---` separators. This is what the training scripts consume.

Options:
```bash
python corpus/build_corpus.py --categories arrival,homesick   # subset
python corpus/build_corpus.py --shuffle                        # randomize order
python corpus/build_corpus.py --stats                          # print category counts
```

## Letter Voice

These are kids writing home. The voice is:
- Short sentences, simple vocabulary
- Spelling and grammar are mostly correct (these are synthetic, not OCR)
- Exclamation points when excited, trailing off when bored
- Concrete details over abstract feelings
- Always starts with "Dear Mom" or "Dear Dad" or "Dear Mom and Dad"
- Usually ends with "Love," or "Miss you," + name
- Names are varied (not all "Tommy")
