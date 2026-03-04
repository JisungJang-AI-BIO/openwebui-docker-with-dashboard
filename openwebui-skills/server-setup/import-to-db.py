#!/usr/bin/env python3
"""
Auto-import Skills & Tools into OpenWebUI database (no API key needed).

Runs INSIDE the OpenWebUI container where:
  - /app/OpenWebUI-Skills/skills/*.md  → skill table
  - /app/OpenWebUI-Skills/tools/*.py   → tool table
  - DATABASE_URL env var               → DB connection

Usage:
  docker exec open-webui python3 /app/OpenWebUI-Skills/server-setup/import-to-db.py
  docker exec open-webui-staging python3 /app/OpenWebUI-Skills/server-setup/import-to-db.py
"""

import os
import sys
import re
import json
import time
import glob
import uuid
import ast
from urllib.parse import urlparse

# ── Config ──────────────────────────────────────────────────────────────────
SKILLS_DIR = "/app/OpenWebUI-Skills/skills"
TOOLS_DIR = "/app/OpenWebUI-Skills/tools"


# ── DB Connection ───────────────────────────────────────────────────────────
def get_db_connection():
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not available. Is this the OpenWebUI container?")
        sys.exit(1)

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set.")
        sys.exit(1)

    parsed = urlparse(db_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.path.lstrip("/"),
    )
    conn.autocommit = True
    return conn


# ── Parse skill .md frontmatter ────────────────────────────────────────────
def parse_skill_md(filepath):
    with open(filepath) as f:
        content = f.read()

    meta = {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if match:
        for line in match.group(1).strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

    basename = os.path.basename(filepath).replace(".md", "")
    return {
        "id": meta.get("name", basename),
        "name": meta.get("name", basename),
        "description": meta.get("description", ""),
        "content": content,
    }


# ── Parse tool .py docstring ───────────────────────────────────────────────
def parse_tool_py(filepath):
    with open(filepath) as f:
        content = f.read()

    meta = {}
    match = re.match(r'^"""(.*?)"""', content, re.DOTALL)
    if not match:
        match = re.match(r"^'''(.*?)'''", content, re.DOTALL)
    if match:
        current_key = None
        for line in match.group(1).strip().split("\n"):
            stripped = line.strip()
            # New key: value
            if re.match(r"^[a-z_]+\s*:", stripped):
                k, v = stripped.split(":", 1)
                k = k.strip().lower().replace(" ", "_")
                meta[k] = v.strip()
                current_key = k
            elif current_key and stripped:
                # Continuation of multi-line value (e.g., description)
                meta[current_key] += " " + stripped

    basename = os.path.basename(filepath).replace(".py", "")
    return {
        "id": basename,
        "name": meta.get("title", basename),
        "description": meta.get("description", ""),
        "content": content,
    }


# ── Access grant: public read, admin-only write ────────────────────────────
def grant_public_read(cur, resource_type, resource_id, now):
    """Insert a wildcard read grant so all users can view/use the resource.
    Write access is NOT granted — only the owner and admins can edit.
    """
    # Check if grant already exists
    cur.execute(
        """
        SELECT 1 FROM access_grant
        WHERE resource_type = %s AND resource_id = %s
          AND principal_type = 'user' AND principal_id = '*' AND permission = 'read'
        """,
        (resource_type, resource_id),
    )
    if cur.fetchone():
        return

    grant_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO access_grant (id, resource_type, resource_id, principal_type, principal_id, permission, created_at)
        VALUES (%s, %s, %s, 'user', '*', 'read', %s)
        """,
        (grant_id, resource_type, resource_id, now),
    )


# ── Generate tool specs via AST parsing ──────────────────────────────────
# Maps Python type annotations → JSON Schema type strings
_TYPE_MAP = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "List": "array",
    "dict": "object",
    "Dict": "object",
}

# Parameters injected by OpenWebUI runtime — not part of the tool's public API
_SKIP_PARAMS = {"self", "__user__", "__event_emitter__", "__event_call__"}


def _annotation_to_type(node):
    """Convert an AST annotation node to a JSON Schema type string."""
    if isinstance(node, ast.Name):
        return _TYPE_MAP.get(node.id, "string")
    if isinstance(node, ast.Constant):
        return _TYPE_MAP.get(str(node.value), "string")
    if isinstance(node, ast.Attribute):
        return _TYPE_MAP.get(node.attr, "string")
    if isinstance(node, ast.Subscript):
        # Optional[X] → unwrap to type of X
        if isinstance(node.value, ast.Name) and node.value.id == "Optional":
            return _annotation_to_type(node.slice)
        if isinstance(node.value, ast.Name):
            return _TYPE_MAP.get(node.value.id, "string")
    return "string"


def generate_specs(tool_id, content):
    """Generate function-calling specs by parsing the Tool source with AST.

    Previous approach used OpenWebUI internals (load_tool_module_by_id +
    get_tool_specs) which produced WRONG specs in the standalone docker-exec
    context — e.g. Python tuple methods (count, index) instead of actual
    Tool class methods.  AST parsing avoids importing the module entirely.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"    (specs: syntax error in {tool_id}: {e})")
        return []

    # Find the Tools class
    tools_cls = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Tools":
            tools_cls = node
            break

    if tools_cls is None:
        print(f"    (specs: no Tools class in {tool_id})")
        return []

    specs = []
    for item in tools_cls.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if item.name.startswith("_"):
            continue

        # Method docstring — use first line as description
        docstring = ast.get_docstring(item) or ""
        description = docstring.strip().split("\n")[0] if docstring else item.name

        # Build parameter schema
        properties = {}
        required = []

        args = item.args
        num_positional = len(args.args)
        num_defaults = len(args.defaults)
        first_default_idx = num_positional - num_defaults

        for i, arg in enumerate(args.args):
            if arg.arg in _SKIP_PARAMS:
                continue

            param_type = "string"
            if arg.annotation:
                param_type = _annotation_to_type(arg.annotation)

            properties[arg.arg] = {
                "type": param_type,
                "description": arg.arg,
            }

            # Required if no default value
            if i < first_default_idx:
                required.append(arg.arg)

        spec = {
            "name": item.name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
        specs.append(spec)

    return specs


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print(" Import Skills & Tools into OpenWebUI DB")
    print("=" * 50)

    conn = get_db_connection()
    cur = conn.cursor()

    # ── Find user_id ──
    # Override with IMPORT_USER_EMAIL env var to import under a specific account
    import_email = os.environ.get("IMPORT_USER_EMAIL", "")
    row = None
    if import_email:
        cur.execute(
            'SELECT id, name FROM "user" WHERE email = %s LIMIT 1', (import_email,)
        )
        row = cur.fetchone()
        if not row:
            print(f"\n  WARNING: User '{import_email}' not found, falling back to admin.")

    if not row:
        cur.execute(
            'SELECT id, name FROM "user" WHERE role = \'admin\' ORDER BY created_at LIMIT 1'
        )
        row = cur.fetchone()
    if not row:
        cur.execute('SELECT id, name FROM "user" ORDER BY created_at LIMIT 1')
        row = cur.fetchone()
    if not row:
        print("\nERROR: No users in database yet.")
        print("Create an admin account in Open WebUI first, then re-run this script.")
        sys.exit(1)

    user_id, user_name = row
    print(f"\n  Owner: {user_name} ({user_id[:8]}...)")

    now = int(time.time())

    # ── Import Skills ──────────────────────────────────────────────────────
    print("\n--- Skills ---")
    skill_new = skill_upd = 0

    for md_path in sorted(glob.glob(f"{SKILLS_DIR}/*.md")):
        skill = parse_skill_md(md_path)

        cur.execute("SELECT 1 FROM skill WHERE id = %s", (skill["id"],))
        exists = cur.fetchone()

        cur.execute(
            """
            INSERT INTO skill (id, user_id, name, description, content, meta, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, true, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                content = EXCLUDED.content,
                updated_at = EXCLUDED.updated_at
            """,
            (
                skill["id"],
                user_id,
                skill["name"],
                skill["description"],
                skill["content"],
                json.dumps({"tags": []}),
                now,
                now,
            ),
        )
        grant_public_read(cur, "skill", skill["id"], now)

        if exists:
            print(f"  [UPD]  {skill['id']}")
            skill_upd += 1
        else:
            print(f"  [NEW]  {skill['id']}")
            skill_new += 1

    print(f"\n  Result: {skill_new} new, {skill_upd} updated")

    # ── Import Tools ───────────────────────────────────────────────────────
    print("\n--- Tools ---")
    tool_new = tool_upd = 0

    for py_path in sorted(glob.glob(f"{TOOLS_DIR}/*.py")):
        tool = parse_tool_py(py_path)

        cur.execute("SELECT 1 FROM tool WHERE id = %s", (tool["id"],))
        exists = cur.fetchone()

        specs = generate_specs(tool["id"], tool["content"])
        meta = {"description": tool["description"], "manifest": {}}

        cur.execute(
            """
            INSERT INTO tool (id, user_id, name, content, specs, meta, valves, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                name = EXCLUDED.name,
                content = EXCLUDED.content,
                specs = EXCLUDED.specs,
                meta = EXCLUDED.meta,
                updated_at = EXCLUDED.updated_at
            """,
            (
                tool["id"],
                user_id,
                tool["name"],
                tool["content"],
                json.dumps(specs),
                json.dumps(meta),
                json.dumps({}),
                now,
                now,
            ),
        )
        grant_public_read(cur, "tool", tool["id"], now)

        if exists:
            print(f"  [UPD]  {tool['id']} ({tool['name']})")
            tool_upd += 1
        else:
            print(f"  [NEW]  {tool['id']} ({tool['name']})")
            tool_new += 1

    print(f"\n  Result: {tool_new} new, {tool_upd} updated")

    cur.close()
    conn.close()

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(" Done!")

    if tool_new > 0:
        print("\n  Next steps (configure Valves for new tools):")
        print("    1. Open WebUI > Workspace > Tools")
        print("    2. Click gear icon on each tool")
        print("    3. Set SCRIPTS_DIR: /app/OpenWebUI-Skills/vendor/<toolname>")
    print("  (Function-calling specs are auto-generated from source.)")

    print("=" * 50)


if __name__ == "__main__":
    main()
