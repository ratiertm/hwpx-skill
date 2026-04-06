#!/usr/bin/env python3
"""License admin CLI — create keys, list users, view stats.

Usage:
    python -m license.admin_cli create --name "홍길동" --email "hong@test.com" --days 365
    python -m license.admin_cli list
    python -m license.admin_cli stats
    python -m license.admin_cli info HWPX-XXXX-XXXX-XXXX-XXXX
    python -m license.admin_cli deactivate HWPX-XXXX-XXXX-XXXX-XXXX
"""
import sys
import argparse
from datetime import datetime, timedelta
from . import db
from .keygen import generate_key


def cmd_create(args):
    key = generate_key()
    expires = None
    if args.days:
        expires = datetime.now() + timedelta(days=args.days)

    db.execute(
        """INSERT INTO licenses (license_key, name, email, organization, plan, max_devices, expires_at, note)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (key, args.name, args.email, args.org, args.plan, args.devices, expires, args.note),
    )
    print(f"\n  License Key: {key}")
    print(f"  Name: {args.name}")
    print(f"  Email: {args.email or '-'}")
    print(f"  Plan: {args.plan}")
    print(f"  Devices: {args.devices}")
    print(f"  Expires: {expires.strftime('%Y-%m-%d') if expires else 'Never'}")
    print()


def cmd_list(args):
    rows = db.query("""
        SELECT l.*,
               COUNT(DISTINCT a.machine_id) FILTER (WHERE a.is_active) as active_devices,
               MAX(a.last_seen) as last_seen
        FROM licenses l
        LEFT JOIN activations a ON l.id = a.license_id
        GROUP BY l.id
        ORDER BY l.created_at DESC
    """)

    if not rows:
        print("No licenses found.")
        return

    print(f"\n{'Key':<28} {'Name':<12} {'Plan':<10} {'Devices':<8} {'Status':<8} {'Expires':<12} {'Last Seen'}")
    print("─" * 100)
    for r in rows:
        status = "✅" if r["is_active"] else "❌"
        if r["expires_at"] and r["expires_at"] < datetime.now():
            status = "⏰"
        expires = r["expires_at"].strftime("%Y-%m-%d") if r["expires_at"] else "Never"
        last = _relative_time(r["last_seen"]) if r["last_seen"] else "Never"
        devs = f"{r['active_devices']}/{r['max_devices']}"
        print(f"  {r['license_key']:<26} {r['name']:<12} {r['plan']:<10} {devs:<8} {status:<8} {expires:<12} {last}")
    print()


def cmd_stats(args):
    total = db.query_one("SELECT COUNT(*) as cnt FROM licenses")["cnt"]
    active = db.query_one("SELECT COUNT(*) as cnt FROM licenses WHERE is_active = TRUE")["cnt"]
    expired = db.query_one(
        "SELECT COUNT(*) as cnt FROM licenses WHERE expires_at < NOW() AND is_active = TRUE"
    )["cnt"]
    today_users = db.query_one(
        "SELECT COUNT(DISTINCT license_id) as cnt FROM usage_logs WHERE created_at > CURRENT_DATE"
    )["cnt"]
    total_logs = db.query_one("SELECT COUNT(*) as cnt FROM usage_logs")["cnt"]

    print(f"""
┌──────────────────────────────────┐
│  HWPX License Stats              │
├──────────────────────────────────┤
│  Total keys:    {total:<16} │
│  Active:        {active:<16} │
│  Expired:       {expired:<16} │
│  Today users:   {today_users:<16} │
│  Total logs:    {total_logs:<16} │
└──────────────────────────────────┘
""")

    # Recent activity
    recent = db.query("""
        SELECT l.name, l.email, ul.action, ul.ip_address, ul.created_at
        FROM usage_logs ul
        JOIN licenses l ON ul.license_id = l.id
        ORDER BY ul.created_at DESC LIMIT 10
    """)
    if recent:
        print("Recent activity:")
        for r in recent:
            ago = _relative_time(r["created_at"])
            print(f"  {r['name']:<12} {r['action']:<12} {r['ip_address'] or '-':<16} {ago}")
        print()


def cmd_info(args):
    lic = db.query_one("SELECT * FROM licenses WHERE license_key = %s", (args.key,))
    if not lic:
        print(f"Key not found: {args.key}")
        return

    print(f"\n  Key:      {lic['license_key']}")
    print(f"  Name:     {lic['name']}")
    print(f"  Email:    {lic['email'] or '-'}")
    print(f"  Org:      {lic['organization'] or '-'}")
    print(f"  Plan:     {lic['plan']}")
    print(f"  Active:   {'✅' if lic['is_active'] else '❌'}")
    print(f"  Created:  {lic['created_at']}")
    print(f"  Expires:  {lic['expires_at'] or 'Never'}")
    print(f"  Note:     {lic['note'] or '-'}")

    devices = db.query(
        "SELECT * FROM activations WHERE license_id = %s ORDER BY last_seen DESC",
        (lic["id"],),
    )
    if devices:
        print(f"\n  Devices ({len(devices)}/{lic['max_devices']}):")
        for d in devices:
            status = "✅" if d["is_active"] else "❌"
            print(f"    {status} {d['machine_name'] or d['machine_id']:<30} IP:{d['ip_address'] or '-':<16} Last:{_relative_time(d['last_seen'])}")

    logs = db.query(
        "SELECT * FROM usage_logs WHERE license_id = %s ORDER BY created_at DESC LIMIT 10",
        (lic["id"],),
    )
    if logs:
        print(f"\n  Recent logs:")
        for l in logs:
            print(f"    {l['created_at'].strftime('%m-%d %H:%M')} {l['action']:<12} {l['ip_address'] or '-'}")
    print()


def cmd_deactivate(args):
    result = db.execute(
        "UPDATE licenses SET is_active = FALSE WHERE license_key = %s",
        (args.key,),
    )
    if result:
        print(f"Deactivated: {args.key}")
    else:
        print(f"Key not found: {args.key}")


def _relative_time(dt):
    if not dt:
        return "Never"
    diff = datetime.now() - dt
    if diff.days > 0:
        return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    minutes = diff.seconds // 60
    return f"{minutes}m ago"


def main():
    parser = argparse.ArgumentParser(description="HWPX License Admin")
    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create", help="Create a new license key")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--email", default=None)
    p_create.add_argument("--org", default=None)
    p_create.add_argument("--plan", default="standard", choices=["standard", "pro", "enterprise"])
    p_create.add_argument("--devices", type=int, default=2)
    p_create.add_argument("--days", type=int, default=None, help="Expiry in days")
    p_create.add_argument("--note", default=None)

    # list
    sub.add_parser("list", help="List all licenses")

    # stats
    sub.add_parser("stats", help="Show usage statistics")

    # info
    p_info = sub.add_parser("info", help="Show license details")
    p_info.add_argument("key")

    # deactivate
    p_deact = sub.add_parser("deactivate", help="Deactivate a license")
    p_deact.add_argument("key")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"create": cmd_create, "list": cmd_list, "stats": cmd_stats,
     "info": cmd_info, "deactivate": cmd_deactivate}[args.command](args)


if __name__ == "__main__":
    main()
