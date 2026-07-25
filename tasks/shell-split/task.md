# shell-split

Implement `split` in `src/wordsplit.py`.

```python
def split(line: str) -> list[str]
```

Split one line of shell-like input into words the way a POSIX shell splits it —
honouring quoting and escaping, and performing **no expansions of any kind**.
`$name`, `$(cmd)`, backticks, `~`, `*`, `?` and `{a,b}` are ordinary text and
survive into the output unchanged.

Throughout this document an input line is written exactly as it would be typed,
and a result is written as a Python repr — so `'a\\b'` in a result is the
three-character word `a`, backslash, `b`.

## Separators

Only the space (`U+0020`) and the tab (`U+0009`) are separators. Every other
character — a newline included — is an ordinary word character unless a rule
below gives it another meaning.

Words are separated by runs of separators; a run of any length ends at most one
word. Leading and trailing separators produce no empty words, so a line that is
empty or holds nothing but separators produces no words at all.

## Words open and close

A word **opens** the moment a character is added to it or a quote is opened, and
**closes** at the next separator. Adjacent runs — quoted or not — belong to the
same word: a quote starts and stops inside a word, it never starts a new one.

```
a"b c"d'e f'      ->  ['ab cde f']
"x"y'z'           ->  ['xyz']
```

A quoted string with nothing in it still opens a word, and so produces an empty
word:

```
x '' y            ->  ['x', '', 'y']
''                ->  ['']
""''              ->  ['']
                  ->  []          (an empty line, and a line of separators only)
```

## Single quotes

From a `'` to the next `'`, every character is literal — backslash included. A
`'` cannot appear inside single quotes; the first one ends them.

```
'a \ b'           ->  ['a \\ b']
'$HOME *.py'      ->  ['$HOME *.py']
'x\'             ->  ['x\\']
```

## Double quotes

From a `"` to the next `"`, every character is literal **except** a backslash
that is immediately followed by one of these five:

| After the backslash | Result                                        |
| ------------------- | --------------------------------------------- |
| `$`                 | a literal `$`, the backslash is dropped        |
| `` ` ``             | a literal `` ` ``, the backslash is dropped    |
| `"`                 | a literal `"`, the backslash is dropped; it does not end the quoting |
| `\`                 | a literal `\`, one backslash is dropped        |
| newline             | both characters vanish (line continuation)     |

Before any other character the backslash is an ordinary literal backslash and
the character after it keeps its own literal meaning.

```
"a\$b"            ->  ['a$b']
"a\\b"            ->  ['a\\b']
"a\nb"            ->  ['a\\nb']
"a\'b"            ->  ["a\\'b"]
```

## Backslash outside quotes

Outside quotes a backslash escapes the character that follows it: that
character is taken literally and joins the current word. This includes a
separator, which then joins the word instead of ending it, and includes `'`,
`"` and `#`.

The one exception is a backslash followed by a newline: it is a line
continuation, both characters vanish, and — unlike a quote — it does **not**
open a word.

```
escaped\ space    ->  ['escaped space']
a\\b              ->  ['a\\b']
\#x               ->  ['#x']
```

## Comments

A `#` outside quotes begins a comment only at the start of a word — that is,
only when no word is currently open. The `#` and every character after it, to
the end of the input, are discarded. Anywhere else `#` is an ordinary
character.

```
run fast # why      ->  ['run', 'fast']
a#b c#d             ->  ['a#b', 'c#d']
# whole line        ->  []
'#' "#" \#          ->  ['#', '#', '#']
```

## Errors

Raise `SplitError` (already defined in `src/wordsplit.py`) when:

- a single or double quote is opened and never closed;
- the last character of the input is a backslash that is not itself escaped —
  a lone trailing backslash has nothing to escape.

Nothing else is an error. `split` never raises anything but `SplitError` for a
`str` argument.

## What you have

`tests/test_visible.py` holds a small suite driven by
`tests/fixtures/cases.json`. Run it with `python -m pytest tests`. It does not
cover the whole specification above — the specification is the contract, not
the test file or the fixture.
