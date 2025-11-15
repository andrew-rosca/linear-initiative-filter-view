# Linear Initiative Filter View

Automatically update Linear roadmap views with custom initiative filters using SQL-like syntax or raw GraphQL queries.

## Why This Tool?

Linear's custom views have limited native filtering capabilities for initiatives. This tool extends what's possible by:

1. **Supporting arbitrary filters** - Filter by any field, including description keywords, complex date logic, or custom criteria
2. **Client-side filtering** - Query all initiatives, apply your custom filter logic, then set the matching initiatives on the view
3. **Automatic sync** - Keep your views up-to-date by re-running filters periodically

The tool works by:
- Running your custom filter query to find matching initiatives
- Creating an ID-based filter (`{"id": {"in": [...]}}`) with the specific initiative IDs
- Setting that filter on your Linear custom view

This means you can filter by things Linear doesn't natively support, like keywords in descriptions or complex boolean logic.

## Features

- **SQL-like filter syntax** - Simple, readable filters like `status = 'started' AND priority > 2`
- **Raw GraphQL queries** - Full power of Linear's GraphQL API for advanced users
- **Multiple views** - Manage multiple roadmap views from a single config file
- **Dry-run mode** - Preview changes before applying them
- **Safe defaults** - Won't clear views if filters return 0 initiatives
- **Clear reporting** - Detailed output showing what changed

## Installation

### Prerequisites

- Python 3.9 or higher
- Linear API token ([get one here](https://linear.app/settings/api))

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/linear-initiative-filter-view.git
cd linear-initiative-filter-view

# Install dependencies
pip install -r requirements.txt

# Install the tool
pip install -e .
```

## Configuration

### 1. Get your Linear API token

1. Go to [Linear Settings > API](https://linear.app/settings/api)
2. Create a new personal API key
3. Copy the token (starts with `lin_api_`)

### 2. Create configuration file

Copy the example config and customize it:

```bash
cp config.toml.example config.toml
```

Edit `config.toml`:

```toml
[linear]
api_token = "lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

[[views]]
title = "High Priority Initiatives"
filter = "priority >= 1"

[[views]]
title = "Q1 2025 Initiatives"
filter = "startDate >= '2025-01-01' AND targetDate <= '2025-03-31'"
```

Alternatively, you can set the `LINEAR_API_TOKEN` environment variable instead of putting it in the config file:

```bash
export LINEAR_API_TOKEN="lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 3. Get your roadmap view identifiers

You can reference views by either:
- **Title**: The exact name of your roadmap view (e.g., "Q1 2025 Initiatives")
- **ID**: The roadmap ID (e.g., "roadmap_abc123")

To find a roadmap ID, you can inspect the URL when viewing it in Linear, or use Linear's GraphQL API explorer.

## Usage

### Sync views (dry-run mode)

By default, the tool runs in dry-run mode to show you what would change:

```bash
linear-filter sync
```

Example output:
```
Loading configuration from config.toml...
Found 2 view(s) to sync

Running in DRY RUN mode - no changes will be made

============================================================
DRY RUN RESULTS
============================================================

✓ High Priority Initiatives
   Total initiatives: 5
   Added: 2
   Removed: 1
   Unchanged: 3

✓ Q1 2025 Initiatives
   Total initiatives: 8
   Added: 3
   Removed: 0
   Unchanged: 5

============================================================
SUMMARY
============================================================
Views processed: 2
Total initiatives: 13
Total added: 5
Total removed: 1

This was a dry run. Use --no-dry-run to apply changes.
```

### Apply changes

Once you've verified the dry-run output, apply the changes:

```bash
linear-filter sync --no-dry-run
```

### Use custom config file

```bash
linear-filter sync --config /path/to/config.toml
```

### Test filter syntax

Test your filter expressions to see the generated GraphQL:

```bash
linear-filter test-filter "status = 'started' AND priority > 2"
```

Output:
```
Input filter: status = 'started' AND priority > 2

Generated GraphQL filter:
{
  "and": [
    {
      "status": {
        "eq": "started"
      }
    },
    {
      "priority": {
        "gt": 2
      }
    }
  ]
}
```

### Export initiatives

Export initiatives from a Linear view to CSV, JSON, or TSV format:

```bash
# Export to CSV (default, outputs to stdout)
linear-filter export --view-title "Q1 2025 Initiatives"

# Export to JSON format
linear-filter export --view-title "Active Initiatives" --format json

# Export to TSV and save to file
linear-filter export --view-id "roadmap_abc123" --format tsv --output initiatives.tsv

# Short options
linear-filter export -t "My View" -f csv -o data.csv
```

**Export formats:**
- `csv` - Comma-separated values (default)
- `json` - JSON format with all initiative data
- `tsv` - Tab-separated values

**Exported fields:**
- ID, Name, Description, Status, Sort Order
- Started At, Target Date, Completed At
- Created At, Updated At, Archived At
- URL, Slug ID, Color, Icon
- Organization, Projects

The export command uses the filter configured on the view itself. If the view has no filter, all initiatives will be exported.

## Filter Syntax

### SQL-like Filters (Simplified)

Use simple, readable SQL-like syntax:

**Comparison operators:**
- `=`, `!=` - Equal, not equal
- `>`, `>=`, `<`, `<=` - Greater/less than

**String operators:**
- `CONTAINS` - String contains substring
- `STARTS_WITH` - String starts with substring
- `ENDS_WITH` - String ends with substring

**Logical operators:**
- `AND` - Both conditions must be true
- `OR` - Either condition must be true
- `NOT` - Negate condition

**Supported fields:**
- `name` - Initiative name
- `status` - Initiative status
- `priority` - Initiative priority (number)
- `startDate`, `start_date` - Start date (ISO format: 'YYYY-MM-DD')
- `targetDate`, `target_date` - Target date (ISO format)
- `description` - Initiative description

**Examples:**

```toml
# Single condition
filter = "status = 'started'"

# Multiple conditions
filter = "status = 'started' AND priority >= 2"

# String matching
filter = "name CONTAINS 'Infrastructure' OR name CONTAINS 'Security'"

# Date ranges
filter = "startDate >= '2025-01-01' AND targetDate <= '2025-12-31'"

# Complex
filter = "(status = 'started' OR status = 'planned') AND priority > 1"
```

### Raw GraphQL Queries (Advanced)

For full control, use raw GraphQL queries:

```toml
[[views]]
title = "Custom Query"
graphql_query = '''
{
  initiatives(filter: {
    status: { eq: "started" }
    priority: { gte: 1 }
    name: { contains: "Infrastructure" }
  }) {
    nodes {
      id
      name
      status
    }
  }
}
'''
```

See [Linear's GraphQL API docs](https://developers.linear.app/docs/graphql/working-with-the-graphql-api) for all available filters.

## Configuration Reference

### Linear Section

```toml
[linear]
# Optional: Linear API token (can also use LINEAR_API_TOKEN env var)
api_token = "lin_api_xxx"
```

### View Section

Each `[[views]]` section defines one roadmap view to manage:

```toml
[[views]]
# Option 1: Identify view by title (exact match)
title = "My Roadmap"

# Option 2: Identify view by ID
view_id = "roadmap_abc123"

# Option 3a: Use simplified filter syntax
filter = "status = 'started' AND priority > 2"

# Option 3b: Use raw GraphQL query (mutually exclusive with filter)
graphql_query = '''
{
  initiatives(filter: { status: { eq: "started" } }) {
    nodes { id }
  }
}
'''
```

**Requirements:**
- Each view must have either `title` OR `view_id`
- Each view must have either `filter` OR `graphql_query` (not both)

## Safety Features

### Dry-run by default
The tool defaults to dry-run mode to prevent accidental changes.

### Zero initiatives warning
If a filter returns 0 initiatives, the tool warns you and skips the update to avoid accidentally clearing a view:

```
⚠️  WARNING: Filter returned 0 initiatives for view 'My View'
   Current view has 5 initiatives
   Skipping update to avoid clearing the view
```

### Error handling
If one view fails to update, other views continue processing. Errors are reported at the end.

## Automation

### Run on a schedule (cron)

```bash
# Edit crontab
crontab -e

# Run every hour
0 * * * * cd /path/to/linear-initiative-filter-view && linear-filter sync --no-dry-run

# Run every 15 minutes
*/15 * * * * cd /path/to/linear-initiative-filter-view && linear-filter sync --no-dry-run
```

### Run via CI/CD

Example GitHub Actions workflow:

```yaml
name: Sync Linear Views
on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:  # Manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install -e .
      - run: linear-filter sync --no-dry-run
        env:
          LINEAR_API_TOKEN: ${{ secrets.LINEAR_API_TOKEN }}
```

## Troubleshooting

### "Config file not found"
Make sure you have a `config.toml` file in your current directory, or use `--config` to specify the path.

### "Linear API token not provided"
Set the `LINEAR_API_TOKEN` environment variable or add `api_token` to your config file.

### "Roadmap not found"
Verify the view title or ID is correct. Titles must match exactly (case-sensitive).

### "Failed to parse filter"
Check your filter syntax. Use `linear-filter test-filter "your filter"` to test it.

### GraphQL errors
If using raw GraphQL queries, verify the syntax with [Linear's API explorer](https://studio.apollographql.com/sandbox/explorer?endpoint=https%3A%2F%2Fapi.linear.app%2Fgraphql).

## Development

```bash
# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests (if added)
pytest

# Format code
black linear_filter/

# Type checking
mypy linear_filter/
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or pull request.

## Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/linear-initiative-filter-view/issues)
- Linear API Docs: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
