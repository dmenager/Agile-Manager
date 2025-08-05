import os
import tempfile
import cl4py
from cl4py import Symbol
import numpy as np
import pandas as pd
DATA_PATH = "~/Code/Data/AgileManager"
state_file = "state.hems"
observation_file = "observation.hems"
action_file = "action.hems"
decisions_df = pd.read_excel(DATA_PATH + "/Decisions.xlsx")
game_sessions_df = pd.read_excel(DATA_PATH + "/Game\ Sessions.xlsx")
#users_df = pd.read_excel(DATA_PATH + "/Users.xlsx")
game_levels_df = pd.read_excel(DATA_PATH + "/Game\ Levels.xlsx")
tasks_df = pd.read_excel(DATA_PATH + "/Tasks.xlsx")
workers_df = pd.read_excel(DATA_PATH + "/Worker\ Agents.xlsx")

unique_sessions = decisions_df["Session ID"].unique()

tasks_dict = dict()
for idx, task in tasks_df.itrerrows():
    task_dict = dict()
    task_id = task["ID"]
    difficulty = task["Difficulty"]
    effort = task["Effort Required"]
    task_dict["Difficulty"] = difficulty
    task_dict["Effort"] = effort
    tasks_dict[task_id] = task_dict
    
for sess_id in unique_sessions:
    sub_df = decisions_df[decisions_df["Session ID"] == sess_id]
    rounds = sub_df["Round"].unique()
    session_data = game_sessions_df[game_sessions_df["ID"] == sess_id]
    agent_task_dict = dict()
    level = session_data["Game Level"]
    level_data = game_levels_df[game_levels_df["Level"] == level]

    productivity_discount = level_data["Average Worker Agent Productivity Output Rate"]
    level_svq = level_data["Speed vs. Quality Trade-off (SvQ)"]
    c = 3
    d = 0
    e = 0
    fp = open(state_file, 'w', encoding="utf-8")
    obs_fp = open(observation_file, 'w', encoding="utf-8")
    act_fp = open(action_file, 'w', encoding="utf-8")
    
    fp.write(bytes(f"c0 = (percept-node level_svq :value \"{level_svq}\")", "utf-8"))
    fp.write(bytes(f"c1 = (percept-node game_level :value \"{level}\")", "utf-8"))
    fp.write(bytes(f"c2 = (percept-node productivity_discount :value \"{productivity_discount}\")", "utf-8"))
    fp.write(bytes(f"c1 --> c0", "utf-8"))
    fp.write(bytes(f"c1 --> c2", "utf-8"))
    for r in rounds:
        round_df = sub_df[sub_df["Round"] == r]
        agents_tasks_quality = dict()
        st_bn = None
        obs_bn = None
        act_bn = None
        fp.write(bytes(f"c{c} = (percept-node round :value \"{r}\")", "utf-8"))
        c += 1
        for idx, row in round_df.iterrows():
            agent_tasks_quality = dict()
            worker_agent_id = row["Worker Agent ID"]
            agent_effort_units = row["Worker Agent Backlog (No. of Effort Units)"]
            agent_tasks_to_complete = set(row["The Backlog Queue"].split(";"))
            agent_reputation = round(row["Worker Agent Reputation"], 1)

            worker_agent = workers_df[workers_df["ID"] == worker_agent_id].iloc[0]
            
            agent_high_quality_output_prob = worker_agent["High Quality Output Probability"]
            agent_max_load = worker_agent["Max Productivity (No. of Effort Units per Round)"]
            scaled_max_load = agent_max_load * productivity_discount
            agent_over_worked_p = True
            if agent_effort_units / scaled_max_load < 1:
                agent_over_worked_p = False
            old_tasks = {}
            new_tasks = {}
            if worker_agent_id in agent_task_dict:
                old_tasks = agent_task_dict[worker_agent_id]
                new_tasks = agent_tasks_to_complete.difference(old_tasks)
            else:
                new_tasks = agent_tasks_to_complete
            agent_task_dict[worker_agent_id] = agent_tasks_to_complete

            obs_fp.write(bytes(f"d{d} = (percept-node agent_{worker_agent_id} :value \"T\")", "utf-8"))
            d_agent = d
            d += 1
            obs_fp.write(bytes(f"d{d} = (percept-node reputation :value \"{agent_reputation}\")", "utf-8"))
            d += 1
            obs_fp.write(bytes(f"d{d-2} --> d{d-1}", "utf-8"))
            for task in old_tasks:
                task_diff = tasks_dict[task]["Difficulty"]
                task_effort = tasks_dict[task]["Effort"]
                obs_fp.write(bytes(f"d{d} = (percept-node task_{task} :value \"T\")", "utf-8"))
                d += 1
                obs_fp.write(bytes(f"d{d} = (percept-node agent :value \"agent_{worker_agent_id}\")", "utf-8"))
                d += 1
                obs_fp.write(bytes(f"d{d} = (percept-node patient :value \"task_{task}\")", "utf-8"))
                d += 1
                obs_fp.write(bytes(f"d{d} = (relation-node responsible :value \"T\")", "utf-8"))
                d += 1
                obs_fp.write(bytes(f"d{d-1} --> d{d-2}"))
                obs_fp.write(bytes(f"d{d-1} --> d{d-3}"))
                obs_fp.write(bytes(f"d{d-2} --> d{d_agent}"))
                obs_fp.write(bytes(f"d{d-3} --> d{d-4}"))
            act_fp.write(bytes(f"e{e} = (percept-node agent_{worker_agent_id} :value \"T\")", "utf-8"))
            e_agent = e
            e += 1
            for task in new_tasks:
                obs_fp.write(bytes(f"e{e} = (percept-node task_{task} :value \"T\")", "utf-8"))
                e += 1
                obs_fp.write(bytes(f"e{e} = (percept-node agent :value \"agent_{worker_agent_id}\")", "utf-8"))
                e += 1
                obs_fp.write(bytes(f"e{e} = (percept-node patient :value \"task_{task}\")", "utf-8"))
                e += 1
                obs_fp.write(bytes(f"e{e} = (relation-node assignment :value \"T\")", "utf-8"))
                e += 1
                obs_fp.write(bytes(f"e{e-1} --> d{e-2}"))
                obs_fp.write(bytes(f"e{e-1} --> d{e-3}"))
                obs_fp.write(bytes(f"e{e-2} --> d{e_agent}"))
                obs_fp.write(bytes(f"e{e-3} --> d{e-4}"))
            for task in agent_tasks_to_complete:
    
                if agent_high_quality_output_prob >= task_diff:
                    agent_tasks_quality[task] = True
                else:
                    agent_tasks_quality[task] = False
            agents_tasks_quality[worker_agent_id] = agent_tasks_quality

            fp.write(bytes(f"c{c} = (percept-node agent_{worker_agent_id} :value \"T\")", "utf-8"))
            c += 1
            fp.write(bytes(f"c{c} = (percept-node max_productivity :value \"{agent_max_load}\")", "utf-8"))
            c += 1
            fp.write(bytes(f"c{c} = (percept-node agent_svq :value \"{agent_high_quality_output_prob}\")", "utf-8"))
            c += 1
            fp.write(bytes(f"c{c-3} --> c{c-2}", "utf-8"))
            fp.write(bytes(f"c{c-3} --> c{c-1}", "utf-8"))
            if agent_overworked-p:
                fp.write(bytes(f"c{c} = (relation-node overworked :value \"T\")", "utf-8"))
                fp.write(bytes(f"c{c} --> c{c-3}", "utf-8"))
        fp.close()
        obs_fp.close()
        act_fp.close()
        st_bn = hems.compile_program_from_file(fp.name)
        obs_bn = hems.compile_program_from_file(obs_fp.name)
        act_bn = hems.compile_program_from_file(act_fp.name)
        os.remove(state_file)
        os.remove(observation_file)
        os.remove(action_file)
    
def setup_hems():
    # get a handle to the lisp subprocess with quicklisp loaded.
    lisp = cl4py.Lisp(cmd=('sbcl', '--dynamic-space-size', '30000',
                           '--script'), quicklisp=True, backtrace=True)
    
    # Start quicklisp and import HEMS package
    lisp.find_package('QL').quickload('HEMS')
    
    # load hems and retain reference.
    hems = lisp.find_package("HEMS")
    return hems
