import streamlit as st
from stqdm import stqdm
import wandb
import time
import os
import json


def check_if_project_already_backed_up(project_name):
    return os.path.exists("./data/" + project_name)


# Assuming wandb has a method for such authentication (this is hypothetical)
def verify_wandb_credentials(username, passkey):
    try:
        # Attempt to authenticate with the given credentials
        wandb.login(username=username, password=passkey)
        return True
    except:
        return False


def fetch_wandb_projects():
    # Placeholder; Fetch a list of projects for the authenticated user from wandb
    projects = []
    return projects


base_path = "./data/"


# Define the two pages of the app
def login_page():
    if not os.path.exists(base_path):
        os.mkdir(base_path)

    wandb_project_page_link = "https://wandb.ai/"
    if st.session_state["credentials_verified"] is None:
        with st.form(key="wandb_form"):
            st.write("### Weights & Biases")
            wandb_signup_page_link = "https://wandb.ai/login?signup=true"
            st.write(
                "Weights & Biases (Wandb) is a machine learning platform designed to help with experiment tracking, dataset versioning and model management. If you already have an account with the platform, you can input your api key and entity name, so that all the experiments can be logged to your personal project (You can also create an account for free [here](%s)). Alternatively, we also provide the option of logging results to the more well known Tensorboard."
                % wandb_signup_page_link
            )

            # this is just a demo...
            wandb_API_key = st.text_input(
                "API key",
                help="Sets the authentication key associated with your account.",
                type="password",
            )
            wandb_api_key_link = "Check your API key [here](https://wandb.ai/authorize)"
            st.markdown(wandb_api_key_link, unsafe_allow_html=True)
            wandb_entity = st.text_input(
                "entity",
                help="The entity associated with your run. Usually this is the same as your wandb username",
            )
            wandb_project = st.text_input(
                "project",
                value="test",
                help="The project associated with your run.",
            )

            wandb_project_page_link += wandb_entity + "/" + wandb_project

            wandb_form_submitted = st.form_submit_button("test connection")

            if wandb_form_submitted:
                try:
                    with st.spinner(
                        "Trying to log a dummy experiment using the supplied info...."
                    ):
                        wandb.login(key=wandb_API_key)
                        wandb_run = wandb.init(
                            entity=wandb_entity, project=wandb_project
                        )
                        wandb_run.finish()

                        time.sleep(2)
                        # delete the wandb run you just created
                        api = wandb.Api()
                        run = api.run(
                            wandb_entity + "/" + wandb_project + "/" + wandb_run.id
                        )
                        run.delete()
                        st.success(
                            "API key + entity combinations looks valid. Experiment results will be logged to your wandb account."
                        )

                        st.session_state["credentials_verified"] = {
                            "entity": wandb_entity,
                            "project": wandb_project,
                            "api_key": wandb_API_key,
                        }
                        st.info(
                            "A test experiment was logged as a test to check if the credentials are valid. The experiment was automatically deleted but it may still be visible in Weights & Biases for a few more minutes"
                        )
                except ValueError:
                    st.error(
                        "API key must be 40 characters long, yours was "
                        + str(len(wandb_API_key))
                    )
                    st.session_state["credentials_verified"] = None
                    pass
                except Exception as e:
                    st.error("API KEY OR ENTITY ARE WRONG. TRY AGAIN")
                    st.session_state["credentials_verified"] = None
                    pass

        if st.session_state["credentials_verified"] is not None:
            st.success(
                "Click [here](%s) to access the Wandb project."
                % wandb_project_page_link
            )

    else:
        if st.session_state["credentials_verified"] is not None:
            st.success(
                "Your wandb credentials have already been validated. Click [here](%s) to access the Wandb project."
                % wandb_project_page_link
            )

        if st.button("Reset wandb login credentials"):
            st.session_state["credentials_verified"] = None
            st.experimental_rerun()


def main_page():
    if st.session_state.credentials_verified or dev_mode:
        st.title("Your Weights & Biases Projects")

        api = wandb.Api()
        projects_list = api.projects(
            "diliadis"
            if dev_mode
            else st.session_state["credentials_verified"]["entity"]
        )

        selected_project = st.selectbox(
            "Available projects", [p.name for p in projects_list]
        )
        # call backup function
        with st.spinner("Counting the number of runs..."):
            runs_list = api.runs(
                # "diliadis" if dev_mode else st.session_state["credentials_verified"]["entity"],
                selected_project,
            )
            st.info(
                "There are " + str(len(runs_list)) + " in project " + selected_project
            )

        project_already_backed_up = check_if_project_already_backed_up(selected_project)

        overwrite_backup = st.checkbox("Overwrite existing backup", value=False)

        if st.button("backup project", disabled=False):
            # first create the project directory
            if not os.path.exists(base_path + selected_project):
                os.mkdir(base_path + selected_project)
            st.info("Saving experiments into json files...")
            for run in stqdm(runs_list):
                temp_id = run.id
                # check if the file exists
                if (
                    not os.path.exists(
                        base_path + selected_project + "/" + temp_id + ".json"
                    )
                    or overwrite_backup
                ):  # check if the experiment file already exists or if the user wants to overwrite it
                    if overwrite_backup:
                        st.toast("Overwriting experiment " + temp_id)
                    temp_config = run.config
                    temp_config["history"] = run.history().to_json()

                    with open(
                        base_path + selected_project + "/" + temp_id + ".json", "w"
                    ) as fp:
                        json.dump(temp_config, fp)
            st.success("Done")

        # if experiments for a given project are already backed up, show a list of them
        # the user should be able to select one experiment and get a quick view of the stored info
        if project_already_backed_up:
            selected_experiment = st.selectbox(
                "Available experiments",
                [
                    exp.split(".json")[0]
                    for exp in os.listdir(base_path + selected_project)
                ],
            )
            if selected_experiment is not None:
                f = open(
                    base_path + selected_project + "/" + selected_experiment + ".json",
                    "r",
                )
                # Reading from file
                exp_data = json.loads(f.read())
                st.json(exp_data)
            else:
                st.info("The project appears to be empty")


# Main flow
if "credentials_verified" not in st.session_state:
    st.session_state.credentials_verified = None

dev_mode = True

menu = ["Login", "Projects"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Login":
    login_page()
else:
    main_page()
