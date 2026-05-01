# python-count-lines

Count lines of code in Python projects with a comment-aware breakdown.

Scans local folders or shallow-clones public git repositories on the fly.

## Installation

```bash
uv tool install python-count-lines
```

Run `pcl -v` to check the installed version.

## Usage

```bash
pcl                                 # current directory
pcl path/to/repo                    # a specific folder
pcl src/app.py                      # a single file
pcl github.com/psf/requests         # a public repo (shorthand)
pcl https://github.com/psf/requests # full URL also works
```

### Output

```
  python-count-lines
  Path:    /home/me/projects/requests

  Folders           4
  Python files     21
  Total lines   6,110
    code        3,125
    docstrings  1,335
    comments      653
    blank         997

  Top 5 largest files
  src/requests/utils.py     1,083
  src/requests/models.py    1,046
  src/requests/sessions.py    833
  src/requests/adapters.py    697
  src/requests/cookies.py     561
```

When `--exclude` is used, the headline rows (folders, files, total) carry a dim
delta showing how much was filtered out:

```
  Folders         1 (-50% of 2)
  Python files    7 (-36% of 11)
  Total lines   427 (-26% of 580)
```

## Remote repositories

If the target looks like a git URL or a shorthand, `pcl` performs a shallow clone
(`--depth 1 --filter=blob:none`) into a temp directory, runs the scan, and cleans up.
`git` must be on `PATH`.

| Form        | Example                                  |
| ----------- | ---------------------------------------- |
| HTTPS       | `https://github.com/psf/requests.git`    |
| SSH         | `git@github.com:psf/requests.git`        |
| `ssh://`    | `ssh://git@github.com/psf/requests.git`  |
| `git://`    | `git://github.com/psf/requests`          |
| Shorthand   | `github.com/psf/requests`                |

Shorthand is also recognised for `gitlab.com`, `bitbucket.org`, and `codeberg.org`.

## Counting rules

Each `.py` file is parsed once; every line is classified into **exactly one** bucket:

| Bucket    | What it is                                                 | How it's detected     |
| --------- | ---------------------------------------------------------- | --------------------- |
| blank     | whitespace-only line                                       | textual               |
| comment   | line whose first non-whitespace character is `#`           | Python `tokenize`     |
| docstring | line inside a module / class / function docstring         | Python `ast`          |
| code      | everything else                                            | by elimination        |

Resolution priority on overlap: `comment > docstring > blank > code`. So a blank line
*inside* a multi-line docstring counts as **docstring** (it's part of the doc content),
while a trailing `# ...` on a code line stays **code**.

Comment detection runs through `tokenize` rather than a regex, so `#` inside string
literals is never mistaken for a comment. If a file has a syntax error, the counter
falls back to a textual scan and still returns sensible numbers.

## Excludes

`--exclude` accepts one or more [`fnmatch`](https://docs.python.org/3/library/fnmatch.html)
patterns. They combine as a logical **OR** — a path is excluded if it matches **any** pattern.

Each pattern is tested two ways:

1. against the **full path** relative to the scan root (e.g. `src/migrations/*`)
2. against **every individual path component**, including the filename
   (e.g. `tests` matches any `tests/` folder; `*_test.py` matches any matching file)

Hidden directories (starting with `.`) and `__pycache__` are skipped by default.

### Examples

```bash
# Folder names — match at any depth
pcl . --exclude tests
pcl . --exclude tests docs

# Anchor a folder pattern to a specific path
pcl . --exclude "src/migrations/*"

# Filename patterns
pcl . --exclude "test_*.py"            # test_foo.py
pcl . --exclude "*_test.py"            # fetch_orders_test.py
pcl . --exclude "*test*.py"            # anything with 'test' in the name

# Combine freely — folders, paths, and filenames at once
pcl . --exclude tests docs "src/migrations/*" "*_test.py" "test_*.py"
```

### Tips

- **Quote glob patterns** (`"*_test.py"`) so the shell doesn't expand them against
  your current directory before `pcl` sees them.
- `--exclude` is greedy (consumes all following words). Put the target **before** it,
  or separate with `--`:
  ```bash
  pcl /repo --exclude tests "*_test.py"           # target first  ✓
  pcl --exclude tests "*_test.py" -- /repo        # -- terminator ✓
  pcl --exclude tests "*_test.py" /repo           # /repo eaten   ✗
  ```

## Flags

| Flag                              | Description                                            |
| --------------------------------- | ------------------------------------------------------ |
| `target`                          | folder, file, or git URL/shorthand. Defaults to `.`    |
| `--exclude PATTERN [PATTERN ...]` | fnmatch patterns to skip                               |
| `--strip-comments`                | exclude comment-only lines from the headline LOC total |
| `-v`, `--version`                 | print the installed version and exit                   |

`--strip-comments` only changes the headline number; the breakdown is always shown.
It composes with everything else:

```bash
pcl github.com/psf/requests --exclude tests docs "*_test.py" --strip-comments
```

## License

MIT
