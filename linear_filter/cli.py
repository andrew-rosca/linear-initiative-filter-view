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
    total_initiatives = 0

    for result in results:
        view_name = result.get("view_name", "Unknown")

        if "error" in result:
            print(f"ERROR {view_name}")
            print(f"   Error: {result['error']}\n")
            errors.append(view_name)
            continue

        skipped = result.get("skipped", False)
        initiatives_changed = result.get("initiatives_changed", False)
        client_side = result.get("client_side_filtering", False)
        
        # Get initiative counts
        initiative_count = result.get("initiative_count", 0)
        old_count = result.get("old_initiative_count", 0)
        added = result.get("added_count", 0)
        removed = result.get("removed_count", 0)
        unchanged = result.get("unchanged_count", 0)
        
        total_initiatives += initiative_count

        if skipped:
            skip_reason = result.get("skip_reason", "Unknown reason")
            print(f"SKIPPED {view_name}")
            print(f"   Reason: {skip_reason}")
            print(f"   Initiatives: {initiative_count} (no change)")
        elif initiatives_changed:
            status = "Would update" if dry_run else "Updated"
            print(f"OK {view_name} ({status})")
            if client_side:
                print(f"   Filtering: Client-side (field not natively supported by Linear)")
            print(f"   Initiatives: {old_count} → {initiative_count}")
            if added > 0:
                print(f"   Added: {added}")
            if removed > 0:
                print(f"   Removed: {removed}")
            if unchanged > 0:
                print(f"   Unchanged: {unchanged}")
            print(f"   Filter: {json.dumps(result.get('filter', {}), indent=6)}")
            updated_count += 1
        else:
            print(f"OK {view_name} (No changes needed)")
            if client_side:
                print(f"   Filtering: Client-side (field not natively supported by Linear)")
            print(f"   Initiatives unchanged")
            print(f"   Initiatives: {initiative_count}")
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
    print(f"Total initiatives: {total_initiatives}")
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


@cli.command()
@click.option(
    "--view-id",
    "-i",
    type=str,
    help="Custom view ID to export initiatives from",
)
@click.option(
    "--view-title",
    "-t",
    type=str,
    help="Custom view title to export initiatives from",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config.toml",
    help="Path to configuration file (default: config.toml)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json", "tsv"], case_sensitive=False),
    default="csv",
    help="Output format (default: csv)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout)",
)
def export(view_id, view_title, config, format, output):
    """Export initiatives from a Linear view to CSV/JSON/TSV.

    You must specify either --view-id or --view-title to identify which view to export.

    Examples:
        linear-filter export --view-title "Active Initiatives"
        linear-filter export --view-id "roadmap_abc123" --format json
        linear-filter export -t "Q1 2025" -f tsv -o initiatives.tsv
    """
    from .exporter import InitiativeExporter

    try:
        # Validate arguments
        if not view_id and not view_title:
            click.echo("Error: You must specify either --view-id or --view-title", err=True)
            sys.exit(1)

        if view_id and view_title:
            click.echo("Error: Specify only one of --view-id or --view-title", err=True)
            sys.exit(1)

        # Load configuration
        click.echo(f"Loading configuration from {config}...", err=True)
        cfg = load_config(config)

        # Create Linear client
        client = LinearClient(api_token=cfg.api_token)

        # Create updater to help find the view
        updater = ViewUpdater(client)

        async def run_export():
            # Find the view
            click.echo(f"Finding view...", err=True)
            if view_id:
                view = await client.get_custom_view_by_id(view_id)
                if not view:
                    raise ValueError(f"View not found with ID: {view_id}")
            else:
                view = await client.get_custom_view_by_name(view_title)
                if not view:
                    raise ValueError(f"View not found with title: {view_title}")

            click.echo(f"Found view: {view['name']} (ID: {view['id']})", err=True)

            # Get the filter from the view
            initiative_filter = view.get("initiativeFilterData")

            if initiative_filter:
                click.echo(f"Fetching initiatives with filter...", err=True)
            else:
                click.echo(f"Fetching all initiatives (no filter set on view)...", err=True)

            # Fetch initiatives
            initiatives = await client.get_initiatives(initiative_filter)

            click.echo(f"Found {len(initiatives)} initiative(s)", err=True)

            # Export to specified format
            exporter = InitiativeExporter(initiatives)

            if output:
                click.echo(f"Writing to {output}...", err=True)
                with open(output, "w", encoding="utf-8") as f:
                    exporter.export(format=format, output=f)
                click.echo(f"Export complete!", err=True)
            else:
                # Write to stdout (messages go to stderr to keep stdout clean)
                exporter.export(format=format, output=sys.stdout)

        # Execute async operation
        asyncio.run(run_export())

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
