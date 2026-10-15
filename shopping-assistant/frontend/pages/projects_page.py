import streamlit as st

import api
from components import product_cards

# Manages the session state for the currently open project.
if "open_project" not in st.session_state:
    st.session_state.open_project = None  # None = show the grid of projects


# Page for managing projects (named groups of products) in the frontend.
def show_project_list():
    st.title("Projects")

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
                if st.button("Open", key=f"open_proj_{p['id']}"):
                    st.session_state.open_project = p["id"]
                    st.rerun()


# Page for viewing and managing the details of a single project.
def show_project_detail(project_id):
    r = api.get(f"/projects/{project_id}/items")
    if not r.ok:  # deleted, or not yours
        st.session_state.open_project = None
        st.rerun()
    data = r.json()
    results = data["results"]
    total = sum(p["price"] for p in results)

    if st.button("← All projects"):
        st.session_state.open_project = None
        st.rerun()

    st.title(data["project"]["name"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Budget needed", f"${total:,.2f}")
    m2.metric("Items", len(results))
    m3.metric("Average price", f"${total / len(results):,.2f}" if results else "–")

    if results:
        product_cards(results, key_prefix=f"proj{project_id}", mode="project", project_id=project_id)
    else:
        st.info("This project is empty. Use 'Add to project' on a product card.")

    st.divider()
    if st.button("Delete this project"):
        api.delete(f"/projects/{project_id}")
        st.session_state.open_project = None
        st.rerun()


if st.session_state.open_project is None:
    show_project_list()
else:
    show_project_detail(st.session_state.open_project)