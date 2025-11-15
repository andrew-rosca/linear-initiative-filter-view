# -*- coding: utf-8 -*-
"""CLI interface for linear-filter tool."""
import asyncio
from pathlib import Path
import sys

import click

from .config import load_config
from .linear_client import LinearClient
from .updater import ViewUpdater


def print_results(results, dry_run=False):
    """Print update results in a readable format.

    Args:
        results: List of update results
        dry_run: Whether this was a dry run
    """
    import json

    mode = "DRY RUN" if dry_run else "UPDATE"
    print(f"\n{'='*60}")
    print(f"{mode} RESULTS")
    print(f"{'='*60}\n")

    updated_count = 0
    skipped_count = 0
    errors = []

    for result in results:
        view_name = result.get("view_name", "Unknown")

        if "error" in result:
            print(f"ERROR {view_name}")
            print(f"   Error: {result['error']}\n")
            errors.append(view_name)
            continue

        skipped = result.get("skipped", False)
        filter_changed = result.get("filter_changed", False)

        if skipped:
            skip_reason = result.get("skip_reason", "Unknown reason")
            print(f"SKIPPED {view_name}")
            print(f"   Reason: {skip_reason}")
        elif filter_changed:
            status = "Would update" if dry_run else "Updated"
            print(f"OK {view_name} ({status})")
            print(f"   Filter changed: Yes")
            if result.get("old_filter"):
                print(f"   Old filter: {json.dumps(result['old_filter'], indent=6)}")
            else:
                print(f"   Old filter: (none)")
            print(f"   New filter: {json.dumps(result['new_filter'], indent=6)}")
            updated_count += 1
        else:
            print(f"OK {view_name} (No changes needed)")
            print(f"   Filter unchanged")
            skipped_count += 1

        print()

    # Summary
    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Views processed: {len(results)}")
    if updated_count > 0:
        print(f"Would update: {updated_count}" if dry_run else f"Updated: {updated_count}")
    if skipped_count > 0:
        print(f"Skipped (no changes): {skipped_count}")
    if errors:
        print(f"Errors: {len(errors)}")
    print()

    if dry_run and updated_count > 0:
        print("This was a dry run. Use --no-dry-run to apply changes.")


@click.group()
def cli():
    """Linear Initiative Filter View - Update Linear views with custom initiative filters."""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config.toml",
    help="Path to configuration file (default: config.toml)",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Preview changes without applying them (default: --dry-run)",
)
def sync(config, dry_run):
    """Sync Linear views with configured filters.

    By default, runs in dry-run mode to preview changes.
    Use --no-dry-run to apply changes.
    """
    try:
        # Load configuration
        print(f"Loading configuration from {config}...")
        cfg = load_config(config)
        print(f"Found {len(cfg.views)} view(s) to sync\n")

        # Create Linear client
        client = LinearClient(api_token=cfg.api_token)

        # Create updater
        updater = ViewUpdater(client)

        # Run updates
        if dry_run:
            print("Running in DRY RUN mode - no changes will be made\n")

        async def run_updates():
            return await updater.update_all_views(cfg.views, dry_run=dry_run)

        # Execute async operation
        results = asyncio.run(run_updates())

        # Print results
        print_results(results, dry_run=dry_run)

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("filter_string")
def test_filter(filter_string):
    """Test a filter expression and see the generated GraphQL.

    Example: linear-filter test-filter "status = 'started' AND priority > 2"
    """
    try:
        from .filter_parser import parse_filter
        import json

        print(f"Input filter: {filter_string}\n")

        graphql_filter = parse_filter(filter_string)

        print("Generated GraphQL filter:")
        print(json.dumps(graphql_filter, indent=2))

    except Exception as e:
        click.echo(f"Error parsing filter: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
