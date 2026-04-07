# R.O.S.E.

ROSE stands for "Recursive organizational structure extractor" and was created as a personal project. It connects to LDAP to extract user information including manager information to construct a tree.

## Environment Variables

All five must be set before running:

| Variable | Purpose |
|---|---|
| `ROSE_HOST` | LDAP server hostname |
| `ROSE_PORT` | LDAP server port |
| `ROSE_UNAME` | Bind username |
| `ROSE_PWORD` | Bind password |
| `ROSE_SEARCH_BASE` | LDAP search base DN |

## Running the CLI Application

### Docker

Copy any CA certificates you need into the `certs/` folder, then build:

```
make
```

Run, passing environment variables through:

```
$ docker run \
    -e ROSE_HOST -e ROSE_PORT \
    -e ROSE_UNAME -e ROSE_PWORD \
    -e ROSE_SEARCH_BASE \
    giuseppe7/rose jhancock

John Hancock
    Jane Doe
    John Doe
```

### Stand-alone Python (uv)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```
uv sync
```

Run the script:

```
$ uv run rose.py jhancock
John Hancock
    Jane Doe
    John Doe
```

Lint:

```
uv run flake8 rose.py
```

## Options

The `<person>` argument accepts either a `sAMAccountName` or an email address.

```
Usage:
 rose <person> [--detailed] [--directsonly|--reverse] [--json] [--exclude-upn=<prefix>] [--exclude-empty-title]
```

### --detailed

Include UPN, email, and title in text output:

```
$ uv run rose.py jhancock --detailed
"John Hancock", "jhancock@example.com", "jhancock@example.com", "CEO"
    "Jane Doe", "jdoe@example.com", "jane.doe@example.com", "VP, Engineering"
```

### --directsonly

Show only the target and their immediate direct reports, without recursing:

```
$ uv run rose.py jhancock --directsonly
John Hancock
    Jane Doe
    John Doe
```

### --reverse

Walk up the reporting chain instead of down:

```
$ uv run rose.py jhancock --reverse
John Hancock
    Jane Doe
        John Smith
```

### --json

Output the full tree as JSON. Always includes `name`, `upn`, `mail`, and `title`.
Downward traversal nests a `directs` array; `--reverse` nests a `manager` object.

```
$ uv run rose.py jhancock --json
{
  "name": "John Hancock",
  "upn": "jhancock@example.com",
  "mail": "john.hancock@example.com",
  "title": "CEO",
  "directs": [
    {
      "name": "Jane Doe",
      "upn": "jdoe@example.com",
      "mail": "jane.doe@example.com",
      "title": "VP, Engineering",
      "directs": []
    }
  ]
}
```

Extract all email addresses from JSON output using `jq`:

```
$ uv run rose.py jhancock --json | jq -r '[.. | objects | .mail // empty] | unique[]'
jane.doe@example.com
john.hancock@example.com
```

To exclude contractors, use `select` with a case-insensitive regex to filter out any entry whose title contains "Contractor":

```
$ uv run rose.py jhancock --json | jq -r '[.. | objects | select(.title | test("Contractor"; "i") | not) | .mail // empty] | unique[]'
jane.doe@example.com
john.hancock@example.com
```

### --exclude-upn=\<prefix\>

Exclude any account whose UPN starts with the given prefix. Useful for filtering out service accounts:

```
$ uv run rose.py jhancock --exclude-upn=svc.
```

### --exclude-empty-title

Exclude accounts with no title set (LDAP returns `[]` for empty attributes):

```
$ uv run rose.py jhancock --exclude-empty-title
```

### Combining filters

Options can be combined freely:

```
$ uv run rose.py jhancock --json --exclude-upn=svc. --exclude-empty-title | \
    jq -r '[.. | objects | .mail // empty] | unique[]'
```

---

## References

1. https://ldap3.readthedocs.io/en/latest/index.html
1. https://www.viget.com/articles/two-ways-to-share-git-hooks-with-your-team/
