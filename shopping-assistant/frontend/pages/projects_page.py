import streamlit as st

import api
from components import product_cards

# Manages the session state for the currently open project.
if "open_project" not in st.session_state:
    st.session_state.open_project = None  # None = show the grid of projects


def error_detail(response, fallback):
    """Pull the backend's error message out of a failed response."""
    try:
        return response.json().get("detail", fallback)
    except ValueError:
        return fallback


# Invitations other people have sent you. Shown at the top of the project list.
def show_invitations():
    r = api.get("/invites")
    if not r.ok or not r.json():
        return
    st.subheader("Invitations")
    for inv in r.json():
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.markdown(f"**{inv['invited_by']}** invited you to **{inv['project_name']}**")
            if c2.button("Accept", key=f"accept_{inv['project_id']}", type="primary"):
                api.post(f"/invites/{inv['project_id']}/accept")
                st.rerun()
            if c3.button("Decline", key=f"decline_{inv['project_id']}"):
                api.post(f"/invites/{inv['project_id']}/decline")
                st.rerun()


# Page for managing projects (named groups of products) in the frontend.
def show_project_list():
    st.title("Projects")
    show_invitations()

    #How a user can create a new project
    with st.form("new_project", clear_on_submit=True):
        name = st.text_input("New project name", placeholder="e.g. Camping trip")
        if st.form_submit_button("Create project"):
            if not name.strip():
                st.error("Give the project a name.")
            else:
                r = api.post("/projects", body={"name": name.strip()})
                if r.ok:
                    st.toast(f"Created '{name.strip()}'")
                    st.rerun()
                else:
                    st.error(f"Couldn't create project ({r.status_code})")

    #Sends a request to the backend to get the list of projects for the current user.
    r = api.get("/projects")
    if not r.ok:
        st.error(f"Couldn't load projects ({r.status_code})")
        return
    projects = r.json()
    if not projects:
        st.info("No projects yet. Create one above, then add products from the Browse page.")
        return

    show_thumbs = st.toggle("Show thumbnails", value=True)
    per_row = 3
    for start in range(0, len(projects), per_row):
        cols = st.columns(per_row)
        for col, p in zip(cols, projects[start:start + per_row]):
            with col.container(border=True):
                st.markdown(f"### {p['name']}")
                if not p["is_owner"]:
                    st.caption(f"👥 Shared by {p['owner']}")
                elif p["shared_with"] > 0:
                    st.caption(f"👥 Shared with {p['shared_with']} {'person' if p['shared_with'] == 1 else 'people'}")
                st.markdown(f"**Budget needed: ${p['total_price']:,.2f}**")
                count = p["item_count"]
                st.caption(f"{count} item{'s' if count != 1 else ''}")

                #Shows thumbnails
                if show_thumbs:
                    thumbs = p["thumbnails"]
                    if thumbs:
                        st.image(thumbs, width=60)  # small row of item pictures

                        # If there are more items than thumbnails, show a "+N more" caption
                        if count > len(thumbs):
                            st.caption(f"+{count - len(thumbs)} more")
                    elif count == 0:
                        st.caption("Empty so far")

                #If the user clicks "Open", set the open_project session state and rerun the app.
                bcol1, bcol2 = st.columns([2, 2])
                with bcol1:
                    if st.button("Open", key=f"open_proj_{p['id']}"):
                        st.session_state.open_project = p["id"]
                        st.rerun()
                with bcol2:
                    # Deleting removes the project for everyone, so ask first. Members can only leave.
                    if p["is_owner"]:
                        with st.popover("Delete"):
                            st.write("Delete this project for everyone?")
                            if st.button("Yes, delete", key=f"confirm_delete_{p['id']}"):
                                api.delete(f"/projects/{p['id']}")
                                st.session_state.open_project = None
                                st.rerun()
                    else:
                        with st.popover("Leave"):
                            st.write("Leave this shared project?")
                            if st.button("Yes, leave", key=f"confirm_leave_{p['id']}"):
                                api.delete(f"/projects/{p['id']}/members/{st.session_state.username}")
                                st.rerun()


# Who is in the project, plus remove / cancel buttons for the owner.
def show_members(project_id, is_owner):
    r = api.get(f"/projects/{project_id}/members")
    if not r.ok:
        return
    data = r.json()
    st.subheader("People")
    st.markdown(f"👑 **{data['owner']}** (owner)")
    for m in data["members"]:
        c1, c2 = st.columns([5, 1])
        label = "invited, hasn't answered yet" if m["status"] == "pending" else m["role"]
        c1.markdown(f"**{m['username']}** ({label})")
        if is_owner:
            button_text = "Cancel invite" if m["status"] == "pending" else "Remove"
            if c2.button(button_text, key=f"rm_member_{project_id}_{m['username']}"):
                api.delete(f"/projects/{project_id}/members/{m['username']}")
                st.rerun()
    if not data["members"]:
        st.caption("Just you so far.")


# Page for viewing and managing the details of a single project.
def show_project_detail(project_id):
    r = api.get(f"/projects/{project_id}/items")
    if not r.ok:  # deleted, you were removed, or not yours
        st.session_state.open_project = None
        st.rerun()
    data = r.json()
    project = data["project"]
    is_owner = project["role"] == "owner"
    results = data["results"]
    total = sum(p["price"] for p in results)

    if st.button("← All projects"):
        st.session_state.open_project = None
        st.rerun()

    # Title on the left, Invite button on the right (only the owner can invite)
    t1, t2 = st.columns([4, 1])
    t1.title(project["name"])
    if not is_owner:
        t1.caption(f"👥 Shared by {project['owner']}. You can add and remove items.")
    if is_owner:
        with t2.popover("➕ Invite"):
            st.write("Invite someone by their username. They'll need to accept before they can see this project.")
            invitee = st.text_input("Username", key=f"invite_name_{project_id}")
            if st.button("Send invite", key=f"send_invite_{project_id}", type="primary"):
                if not invitee.strip():
                    st.error("Enter a username.")
                else:
                    resp = api.post(f"/projects/{project_id}/invites", body={"username": invitee.strip()})
                    if resp.ok:
                        st.toast(f"Invitation sent to {invitee.strip()}")
                        st.rerun()
                    else:
                        st.error(error_detail(resp, "Couldn't send the invitation."))

    m1, m2, m3 = st.columns(3)
    m1.metric("Budget needed", f"${total:,.2f}")
    m2.metric("Items", len(results))
    m3.metric("Average price", f"${total / len(results):,.2f}" if results else "–")

    if results:
        product_cards(results, key_prefix=f"proj{project_id}", mode="project", project_id=project_id)
    else:
        st.info("This project is empty. Use 'Add to project' on a product card.")

    st.divider()
    show_members(project_id, is_owner)

    st.divider()
    if is_owner:
        with st.popover("Delete this project"):
            st.write("Delete this project for everyone?")
            if st.button("Yes, delete", key=f"confirm_delete_detail_{project_id}"):
                api.delete(f"/projects/{project_id}")
                st.session_state.open_project = None
                st.rerun()
    else:
        with st.popover("Leave this project"):
            st.write("Leave this shared project?")
            if st.button("Yes, leave", key=f"confirm_leave_detail_{project_id}"):
                api.delete(f"/projects/{project_id}/members/{st.session_state.username}")
                st.session_state.open_project = None
                st.rerun()


if st.session_state.open_project is None:
    show_project_list()
else:
    show_project_detail(st.session_state.open_project)