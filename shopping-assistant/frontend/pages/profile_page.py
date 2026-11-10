import streamlit as st

import api
from components import show_recovery_code

st.title("Your profile")
st.caption("Your shopping preferences help the recommendation agents find products that fit you.")

response = api.get_profile()
if not response.ok:
    st.error("Couldn't load your profile.")
    st.stop()
profile = response.json()

with st.form("shopping_profile"):
    st.subheader("About you")
    display_name = st.text_input("Display name", value=profile.get("display_name") or "")
    interests = st.text_area("Interests and shopping needs", value=profile.get("interests") or "",
                             placeholder="e.g. college student, hiking, gaming, home office")
    st.subheader("Budget")
    c1, c2 = st.columns(2)
    budget_min = c1.number_input("Minimum budget ($)", min_value=0.0, value=float(profile["budget_min"] or 0),
                                 step=10.0)
    budget_max = c2.number_input("Maximum budget ($)", min_value=0.0, value=float(profile["budget_max"] or 0),
                                 step=10.0, help="Set to 0 for no maximum.")
    st.subheader("Product preferences")
    categories = api.get("/categories")
    available_categories = categories.json() if categories.ok else []
    preferred_categories = st.multiselect("Favorite categories", available_categories,
                                          default=[x for x in profile.get("preferred_categories", []) if x in available_categories])
    preferred_brands = st.text_input("Preferred brands (comma-separated)",
                                     value=", ".join(profile.get("preferred_brands", [])))
    avoided_brands = st.text_input("Brands to avoid (comma-separated)",
                                   value=", ".join(profile.get("avoided_brands", [])))
    preferred_retailers = st.text_input("Preferred retailers (comma-separated)",
                                        value=", ".join(profile.get("preferred_retailers", [])))
    profile_notes = st.text_area("Additional preferences", value=profile.get("profile_notes") or "",
                                 placeholder="e.g. prioritize durable products and good warranties")
    saved = st.form_submit_button("Save shopping profile", type="primary", use_container_width=True)

if saved:
    if budget_min and budget_max and budget_min > budget_max:
        st.error("Minimum budget cannot exceed maximum budget.")
    else:
        split = lambda value: [part.strip() for part in value.split(",") if part.strip()]
        updated = api.update_profile(
            display_name=display_name,
            interests=interests,
            budget_min=budget_min or None,
            budget_max=budget_max or None,
            preferred_categories=preferred_categories,
            preferred_brands=split(preferred_brands),
            avoided_brands=split(avoided_brands),
            preferred_retailers=split(preferred_retailers),
            profile_notes=profile_notes,
        )
        if updated.ok:
            st.success("Your shopping profile has been saved. New recommendations will use these preferences.")
            st.rerun()
        else:
            st.error(updated.json().get("detail", "Could not save your profile."))

st.divider()
st.subheader("Account security")
with st.form("change_password", clear_on_submit=True):
    current = st.text_input("Current password", type="password")
    new_pw = st.text_input("New password (8+ characters)", type="password")
    confirm = st.text_input("Confirm new password", type="password")
    if st.form_submit_button("Change password"):
        if not (current and new_pw):
            st.error("Fill in every field.")
        elif new_pw != confirm:
            st.error("The two new passwords don't match.")
        else:
            ok, msg = api.change_password(current, new_pw)
            (st.success if ok else st.error)(msg)

st.subheader("Recovery code")
st.caption("A new code invalidates the previous one. Store it somewhere safe.")
if st.session_state.get("recovery_to_show"):
    if show_recovery_code(st.session_state.recovery_to_show, "dismiss_profile_code"):
        del st.session_state["recovery_to_show"]
        st.rerun()
else:
    with st.form("new_code_form", clear_on_submit=True):
        pw = st.text_input("Confirm your password", type="password")
        if st.form_submit_button("Generate new recovery code"):
            ok, result = api.new_recovery_code(pw)
            if ok:
                st.session_state.recovery_to_show = result
                st.rerun()
            else:
                st.error(result)
