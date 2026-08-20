"""Remove duplicate (site_id, ts) rows from sensor_data before the unique
constraint (migration 0011) is applied.

For every (site_id, ts) that has more than one row, the LOWEST id is kept and the
rest are deleted (they are byte-for-byte re-sends of the same burst). Runs against
the configured production DB via app.core.db.

Usage:
    python -m app.scripts.dedup_sensor_data           # dry-run: report only
    python -m app.scripts.dedup_sensor_data --apply    # delete duplicate copies

Always run the dry-run first and eyeball the counts. Take a DB backup before
--apply. After --apply reports 0 remaining duplicates, apply migration 0011.
"""
import asyncio
import sys

from sqlalchemy import text

from app.core.db import SessionLocal

_DUP_GROUPS = text(
    "SELECT COUNT(*) FROM "
    "(SELECT site_id, ts FROM sensor_data GROUP BY site_id, ts HAVING COUNT(*) > 1) g"
)
_DUP_ROWS = text(
    "SELECT COALESCE(SUM(c - 1), 0) FROM "
    "(SELECT COUNT(*) AS c FROM sensor_data GROUP BY site_id, ts HAVING COUNT(*) > 1) x"
)
# MySQL multi-table delete: keep the smallest id per (site_id, ts).
_DELETE_DUPES = text(
    "DELETE t FROM sensor_data t "
    "JOIN (SELECT site_id, ts, MIN(id) AS keep_id FROM sensor_data "
    "      GROUP BY site_id, ts HAVING COUNT(*) > 1) d "
    "  ON t.site_id = d.site_id AND t.ts = d.ts AND t.id <> d.keep_id"
)


async def _run(apply: bool) -> int:
    async with SessionLocal() as db:
        groups = (await db.execute(_DUP_GROUPS)).scalar() or 0
        rows = int((await db.execute(_DUP_ROWS)).scalar() or 0)
        print(f"Duplicate (site_id, ts) groups: {groups}")
        print(f"Duplicate rows to remove (keeping oldest per group): {rows}")
        if not apply:
            print("\nDry-run only. Re-run with --apply to delete the duplicate copies.")
            return 0
        if rows == 0:
            print("\nNothing to delete.")
            return 0
        result = await db.execute(_DELETE_DUPES)
        await db.commit()
        remaining = (await db.execute(_DUP_GROUPS)).scalar() or 0
        print(f"\nDeleted {result.rowcount} duplicate row(s).")
        print(f"Remaining duplicate groups: {remaining} (should be 0)")
        return 0


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    return asyncio.run(_run(apply))


if __name__ == "__main__":
    raise SystemExit(main())
