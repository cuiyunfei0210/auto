# auto

Command-line client for [RANDOM.ORG](https://www.random.org/) true random integers.

Each run you specify **how many** numbers and the **inclusive range**. RANDOM.ORG generates the values from atmospheric noise. This tool does not let you pick or fake the output numbers.

## Usage

Python 3.9+; no extra packages.

Interactive (prompts for count / min / max each time):

```bash
python3 random_org.py
```

One-shot:

```bash
python3 random_org.py --num 5 --min 1 --max 100
```

Unique numbers (no duplicates):

```bash
python3 random_org.py --num 6 --min 1 --max 49 --unique
```

Check remaining bit quota:

```bash
python3 random_org.py --quota
```

Comma-separated output:

```bash
python3 random_org.py --num 3 --min 1 --max 10 --sep ','
```

Optional: set `RANDOM_ORG_EMAIL` so RANDOM.ORG can contact you if the client misbehaves (their automated-client guideline).

```bash
export RANDOM_ORG_EMAIL="you@example.com"
```

## Tests

```bash
python3 test_random_org.py
```
