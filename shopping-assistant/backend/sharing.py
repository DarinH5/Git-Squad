"""
Project sharing: invitations, members, and permission checks.

Hook it into main.py with two lines at the very bottom (after all other routes):

    import sharing
    sharing.register(app, get_db, get_current_user, DB_PATH)

This file owns ALL of the /projects routes (create, list, delete, items), because every one of
them now has to ask "is this person the owner, or an accepted member?". So delete the old
"Projects" section from main.py, or the old routes will be matched first.

Roles:  owner   = the person who created the project (projects.user_id)
        editor  = an invited person who accepted; can add and remove items
Only the owner can invite people, remove other members, or delete the project.
"""
import sqlite3

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class InviteRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)


def init_tables(db_path):
    """Create the sharing table and upgrade project_items in place (safe to run every start)."""
    with sqlite3.connect(db_path) as conn:
        # One row per invited person. status is 'pending' until they accept.
        conn.execute(
            """CREATE TABLE IF NOT EXISTS project_members (
                project_id INTEGER NOT NULL REFERENCES projects(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                role TEXT NOT NULL DEFAULT 'editor',
                status TEXT NOT NULL DEFAULT 'pending',
                invited_by INTEGER REFERENCES users(id),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, user_id)
            )"""
        )
        # Remember who added each item, so shared projects can show it
        columns = [row[1] for row in conn.execute("PRAGMA table_info(project_items)")]
        if "added_by" not in columns:
            conn.execute("ALTER TABLE project_items ADD COLUMN added_by INTEGER REFERENCES users(id)")


def get_access(db, project_id, user_id):
    """Return (project_row, role) or raise 404.

    The role is 'owner' or 'editor'. Someone with no access gets the same 404 as a project that
    doesn't exist, so people can't discover which project ids exist.
    """
    project = db.execute(
        "SELECT p.id, p.name, p.user_id AS owner_id, u.username AS owner_username "
        "FROM projects p JOIN users u ON u.id = p.user_id WHERE p.id = ?",
        (project_id,),
    ).fetchone()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["owner_id"] == user_id:
        return project, "owner"
    member = db.execute(
        "SELECT role FROM project_members WHERE project_id = ? AND user_id = ? AND status = 'accepted'",
        (project_id, user_id),
    ).fetchone()
    if member is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project, member["role"]


def need(role, allowed):
    """Raise 403 unless the person's role is allowed to do this action."""
    if role not in allowed:
        raise HTTPException(status_code=403, detail="You don't have permission to do that")


def register(app, get_db, get_current_user, db_path):
    init_tables(db_path)

    # ---------- Projects ----------
    @app.post("/projects", status_code=201)
    def create_project(
        body: ProjectCreate,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name can't be blank")
        cur = db.execute("INSERT INTO projects (user_id, name) VALUES (?, ?)", (user["id"], name))
        db.commit()
        return {"id": cur.lastrowid, "name": name}

    @app.get("/projects")
    def list_projects(user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
        me = user["id"]
        # Projects I own, plus projects I've accepted an invite to
        rows = db.execute(
            "SELECT p.id, p.name, u.username AS owner, (p.user_id = ?) AS is_owner, "
            "COUNT(pi.product_id) AS item_count, COALESCE(SUM(pr.price), 0) AS total_price, "
            "(SELECT COUNT(*) FROM project_members m WHERE m.project_id = p.id AND m.status = 'accepted') "
            "AS shared_with "
            "FROM projects p JOIN users u ON u.id = p.user_id "
            "LEFT JOIN project_items pi ON pi.project_id = p.id "
            "LEFT JOIN products pr ON pr.id = pi.product_id "
            "WHERE p.user_id = ? OR p.id IN "
            "(SELECT project_id FROM project_members WHERE user_id = ? AND status = 'accepted') "
            "GROUP BY p.id ORDER BY is_owner DESC, p.id",
            (me, me, me),
        ).fetchall()
        projects = [dict(r) for r in rows]

        # Thumbnails: image URLs of the items in each project (newest first)
        images = {}
        if projects:
            marks = ",".join("?" * len(projects))
            image_rows = db.execute(
                "SELECT pi.project_id, pr.image_url FROM project_items pi "
                "JOIN products pr ON pr.id = pi.product_id "
                f"WHERE pi.project_id IN ({marks}) AND pr.image_url IS NOT NULL AND pr.image_url != '' "
                "ORDER BY pi.added_at DESC, pi.rowid DESC",
                [p["id"] for p in projects],
            ).fetchall()
            for r in image_rows:
                images.setdefault(r["project_id"], []).append(r["image_url"])

        for p in projects:
            p["is_owner"] = bool(p["is_owner"])
            p["total_price"] = round(p["total_price"], 2)
            p["thumbnails"] = images.get(p["id"], [])[:4]
        return projects

    @app.delete("/projects/{project_id}")
    def delete_project(
        project_id: int,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        _, role = get_access(db, project_id, user["id"])
        need(role, ("owner",))
        db.execute("DELETE FROM project_items WHERE project_id = ?", (project_id,))
        db.execute("DELETE FROM project_members WHERE project_id = ?", (project_id,))
        db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        db.commit()
        return {"message": "Project deleted"}

    # ---------- Items ----------
    @app.get("/projects/{project_id}/items")
    def list_project_items(
        project_id: int,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        project, role = get_access(db, project_id, user["id"])
        rows = db.execute(
            "SELECT p.*, u.username AS added_by FROM project_items pi "
            "JOIN products p ON p.id = pi.product_id "
            "LEFT JOIN users u ON u.id = pi.added_by "
            "WHERE pi.project_id = ? ORDER BY pi.added_at DESC, pi.rowid DESC",
            (project_id,),
        ).fetchall()
        return {
            "project": {
                "id": project["id"], "name": project["name"],
                "owner": project["owner_username"], "role": role,
            },
            "results": [dict(r) for r in rows],
        }

    @app.post("/projects/{project_id}/items", status_code=201)
    def add_project_item(
        project_id: int,
        product_id: int,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        _, role = get_access(db, project_id, user["id"])
        need(role, ("owner", "editor"))
        if db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="Product not found")
        cur = db.execute(
            "INSERT OR IGNORE INTO project_items (project_id, product_id, added_by) VALUES (?, ?, ?)",
            (project_id, product_id, user["id"]),
        )
        db.commit()
        return {"message": "Added" if cur.rowcount else "Already in project"}

    @app.delete("/projects/{project_id}/items/{product_id}")
    def remove_project_item(
        project_id: int,
        product_id: int,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        _, role = get_access(db, project_id, user["id"])
        need(role, ("owner", "editor"))
        db.execute(
            "DELETE FROM project_items WHERE project_id = ? AND product_id = ?", (project_id, product_id)
        )
        db.commit()
        return {"message": "Removed"}

    # ---------- Members and invitations ----------
    @app.get("/projects/{project_id}/members")
    def list_members(
        project_id: int,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        project, role = get_access(db, project_id, user["id"])
        rows = db.execute(
            "SELECT u.username, m.role, m.status FROM project_members m "
            "JOIN users u ON u.id = m.user_id WHERE m.project_id = ? ORDER BY m.status, u.username",
            (project_id,),
        ).fetchall()
        # Only the owner can see who has been invited but hasn't answered yet
        members = [dict(r) for r in rows if role == "owner" or r["status"] == "accepted"]
        return {"owner": project["owner_username"], "role": role, "members": members}

    @app.post("/projects/{project_id}/invites", status_code=201)
    def invite_member(
        project_id: int,
        body: InviteRequest,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        _, role = get_access(db, project_id, user["id"])
        need(role, ("owner",))
        invitee = db.execute("SELECT id FROM users WHERE username = ?", (body.username.strip(),)).fetchone()
        if invitee is None:
            raise HTTPException(status_code=404, detail="No user with that username")
        if invitee["id"] == user["id"]:
            raise HTTPException(status_code=400, detail="You can't invite yourself")
        existing = db.execute(
            "SELECT status FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, invitee["id"]),
        ).fetchone()
        if existing:
            detail = "Already a member" if existing["status"] == "accepted" else "Already invited"
            raise HTTPException(status_code=409, detail=detail)
        db.execute(
            "INSERT INTO project_members (project_id, user_id, role, status, invited_by) "
            "VALUES (?, ?, 'editor', 'pending', ?)",
            (project_id, invitee["id"], user["id"]),
        )
        db.commit()
        return {"message": "Invitation sent"}

    @app.delete("/projects/{project_id}/members/{username}")
    def remove_member(
        project_id: int,
        username: str,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        """The owner can remove anyone (or cancel an invite). A member can remove only themselves (leave)."""
        _, role = get_access(db, project_id, user["id"])
        if role != "owner" and username != user["username"]:
            raise HTTPException(status_code=403, detail="You don't have permission to do that")
        target = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if target is None:
            raise HTTPException(status_code=404, detail="Member not found")
        cur = db.execute(
            "DELETE FROM project_members WHERE project_id = ? AND user_id = ?", (project_id, target["id"])
        )
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Member not found")
        return {"message": "Removed"}

    @app.get("/invites")
    def my_invites(user: dict = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
        rows = db.execute(
            "SELECT m.project_id, p.name AS project_name, u.username AS invited_by "
            "FROM project_members m JOIN projects p ON p.id = m.project_id "
            "JOIN users u ON u.id = m.invited_by "
            "WHERE m.user_id = ? AND m.status = 'pending' ORDER BY m.created_at DESC",
            (user["id"],),
        ).fetchall()
        return [dict(r) for r in rows]

    @app.post("/invites/{project_id}/accept")
    def accept_invite(
        project_id: int,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        cur = db.execute(
            "UPDATE project_members SET status = 'accepted' "
            "WHERE project_id = ? AND user_id = ? AND status = 'pending'",
            (project_id, user["id"]),
        )
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invitation not found")
        return {"message": "Invitation accepted"}

    @app.post("/invites/{project_id}/decline")
    def decline_invite(
        project_id: int,
        user: dict = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db),
    ):
        cur = db.execute(
            "DELETE FROM project_members WHERE project_id = ? AND user_id = ? AND status = 'pending'",
            (project_id, user["id"]),
        )
        db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invitation not found")
        return {"message": "Invitation declined"}
