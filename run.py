import tempfile
import cl4py
from cl4py import Symbol
import numpy as np
import pandas as pd
DATA_PATH = "~/Code/Data/AgileManager"
decisions_df = pd.read_excel(DATA_PATH + "/Decisions.xlsx")
game_sessions_df = pd.read_excel(DATA_PATH + "/Game\ Sessions.xlsx")
#users_df = pd.read_excel(DATA_PATH + "/Users.xlsx")
game_levels_df = pd.read_excel(DATA_PATH + "/Game\ Levels.xlsx")
tasks_df = pd.read_excel(DATA_PATH + "/Tasks.xlsx")
workers_df = pd.read_excel(DATA_PATH + "/Worker\ Agents.xlsx")

unique_sessions = decisions_df["Session ID"].unique()
for sess_id in unique_sessions:
    sub_df = decisions_df[decisions_df["Session ID"] == sess_id]
    rounds = sub_df["Round"].unique()
    session_data = game_sessions_df[game_sessions_df["ID"] == sess_id]
    agent_task_dict = dict()
    for r in rounds:
        round_df = sub_df[sub_df["Round"] == r]
        for idx, row in round_df.iterrows():
            worker_agent_id = row["Worker Agent ID"]
            agent_effort_units = row["Worker Agent Backlog (No. of Effort Units)"]
            agent_tasks_to_complete = set(row["The Backlog Queue"].split(";"))
            agent_reputation = round(row["Worker Agent Reputation"], 1)

            old_tasks = {}
            new_tasks = {}
            if worker_agent_id in agent_task_dict:
                old_tasks = agent_task_dict[worker_agent_id]
                new_tasks = agent_tasks_to_complete.difference(old_tasks)
            else:
                new_tasks = agent_tasks_to_complete

            agent_task_dict[worker_agent_id] = agent_tasks_to_complete
    
def setup_hems():
    # get a handle to the lisp subprocess with quicklisp loaded.
    lisp = cl4py.Lisp(cmd=('sbcl', '--dynamic-space-size', '30000',
                           '--script'), quicklisp=True, backtrace=True)
    
    # Start quicklisp and import HEMS package
    lisp.find_package('QL').quickload('HEMS')
    
    # load hems and retain reference.
    hems = lisp.find_package("HEMS")
    return hems
