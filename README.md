# count-lines

Count lines of code across multiple languages with a comment-aware breakdown.

Supports Python, JavaScript (incl. JSX), TypeScript (incl. TSX), and Rust. Scans local folders or shallow-clones public git repositories on the fly.

## Supported languages

| Language    | Extensions             |
| ----------- | ---------------------- |
| Python      | `.py`                  |
| JavaScript  | `.js`, `.mjs`, `.cjs`  |
| JSX         | `.jsx`                 |
| TypeScript  | `.ts`                  |
| TSX         | `.tsx`                 |
| Rust        | `.rs`                  |

JSX files are parsed with the JavaScript grammar (the modern JS grammar
handles JSX natively).

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
  count-lines
  Path:    /home/me/projects/mixed-app

  Folders          12
  Source files    47
    typescript    28
    rust          12
    python         7
  Total lines  9,820
    code       6,540
    doc lines  1,180
    comments     520
    blank      1,580

  Top 5 largest files
  backend/src/lib.rs              1,420
  web/src/components/App.tsx        984
  backend/src/handlers.rs           910
  web/src/utils/parser.ts           802
  scripts/migrate.py                610
```

When `--exclude` is used, the headline rows (folders, files, total) carry a dim
delta showing how much was filtered out:

```
  Folders         1 (-50% of 2)
  Source files    7 (-36% of 11)
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

Each supported source file is parsed once via tree-sitter; every line is
classified into **exactly one** bucket:

| Bucket    | What it is                                                                                                  |
| --------- | ----------------------------------------------------------------------------------------------------------- |
| blank     | whitespace-only line                                                                                        |
| comment   | line inside a non-doc comment (e.g. `#` in Python, `//` and `/* */` in JS/TS/Rust)                          |
| doc       | Python module/class/function docstrings, JSDoc `/** */`, Rust `///`, `//!`, `/** */`, `/*! */`              |
| code      | everything else                                                                                             |

Resolution priority on overlap: `comment > doc > blank > code`. So a blank line
*inside* a multi-line docstring counts as **doc** (it's part of the doc content),
while a trailing `# ...` on a code line stays **code**.

Tree-sitter parses each file; comment-only and string-literal nodes are mapped
to the right bucket per language. Strings containing `//` or `#` are never
mistaken for comments. On parse errors tree-sitter's error recovery still
surfaces well-formed regions.

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

| Flag                              | Description                                                       |
| --------------------------------- | ----------------------------------------------------------------- |
| `target`                          | folder, file, or git URL/shorthand. Defaults to `.`               |
| `--exclude PATTERN [PATTERN ...]` | fnmatch patterns to skip                                          |
| `--lang NAME [NAME ...]`          | limit counting to the named languages (default: all supported)    |
| `--strip-comments`                | exclude comment-only lines from the headline LOC total            |
| `-v`, `--version`                 | print the installed version and exit                              |

`--strip-comments` only changes the headline number; the breakdown is always shown.
It composes with everything else:

```bash
pcl github.com/psf/requests --exclude tests docs "*_test.py" --strip-comments
```

## License

MIT
