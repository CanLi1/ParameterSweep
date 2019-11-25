__author__ = "Cristiana L. Lara"
# Stochastic Dual Dynamic Integer Programming (SDDiP) description at:
# https://link.springer.com/content/pdf/10.1007%2Fs10107-018-1249-5.pdf

# This algorithm scenario tree satisfies stage-wise independence

import time
import math
import random
from copy import deepcopy
import os.path
from pyomo.environ import *
import csv


from scenarioTree import create_scenario_tree
import deterministic.readData_det as readData_det
import deterministic.optBlocks_det as b


# ######################################################################################################################
# USER-DEFINED PARAMS

# Define case-study
curPath = os.path.abspath(os.path.curdir)
curPath = curPath.replace('/deterministic', '')

# filepath = os.path.join(curPath, 'data/GTEPdata_2020_2034_no_nuc.db')
filepath = os.path.join(curPath, 'data/GTEP_data_15years.db')
# filepath = os.path.join(curPath, 'data/GTEPdata_2020_2039.db')
# filepath = os.path.join(curPath, 'data/GTEPdata_2020_2024.db')
# filepath = os.path.join(curPath, 'data/GTEPdata_2020_2029.db')

n_stages = 15  # number od stages in the scenario tree
stages = range(1, n_stages + 1)
scenarios = ['M']
single_prob = {'M': 1.0}

# time_periods = 10
time_periods = 15
set_time_periods = range(1, time_periods + 1)
# t_per_stage = {1:[1], 2:[2], 3:[3]}
# t_per_stage = {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8], 5: [9, 10]}
# t_per_stage = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5]}
# t_per_stage = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [6], 7: [7], 8: [8], 9: [9], 10: [10]}
t_per_stage = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [6], 7: [7], 8: [8], 9: [9], 10: [10],
               11: [11], 12: [12], 13: [13], 14: [14], 15: [15]}



# create scenarios and input data
nodes, n_stage, parent_node, children_node, prob, sc_nodes = create_scenario_tree(stages, scenarios, single_prob)
readData_det.read_data(filepath, curPath, stages, n_stage, t_per_stage)
sc_headers = list(sc_nodes.keys())






# Map stage by time_period
stage_per_t = {t: k for k, v in t_per_stage.items() for t in v}



# create blocks
max_iter=100
m = b.create_model(n_stages, time_periods, t_per_stage, max_iter)
start_time = time.time()

# converting sets to lists:
rn_r = list(m.rn_r)
th_r = list(m.th_r)
j_r = [(j, r) for j in m.j for r in m.r]


#=================================start Parameter sweep =====================
#m.Qg_np: generator nameplate capacity (MW)
# m.CCm: capital cost multiplier of generator cluster i (unitless)
#m.Pg_min: minimum operating output of a generator in cluster i ∈ ITH (fraction of the nameplate capacity)
# m.Ru_max: maximum ramp-up rate for cluster i ∈ ITH (fraction of nameplate capacity)
# m.Rd_max: maximum ramp-down rate for cluster i ∈ ITH (fraction of nameplate capacity)
# m.hr: heat rate of generator cluster i (MMBtu/MWh)
# m.EF_CO2: full lifecycle CO2 emission factor for generator cluster i (kgCO2/MMBtu)


Qg_np_ratio = [0.5, 0.75, 1.0, 1.25]
Pg_min_params = [0, 0.15, 0.3, 0.45]
ramp_params =  [0.15, 0.25, 0.35]
hr_params = [5, 10, 15]
EF_CO2_ratio = [0.5, 0.75, 1.0]

p1, p2, p3, p4, p5 = 0, 0, 0, 0, 0

i_r_keys = [('coal-first-new', 'Northeast'), ('coal-first-new', 'West'), ('coal-first-new', 'Coastal'), ('coal-first-new', 'South'), ('coal-first-new', 'Panhandle')]
for key in i_r_keys:
    m.Qg_np[key] = readData_det.Qg_np[key] * Qg_np_ratio[p1]
m.CCm['coal-first-new'] = readData_det.CCm['coal-first-new'] * pow(Qg_np_ratio[p1], 0.55)

m.Pg_min['coal-first-new'] = Pg_min_params[p2]

m.Ru_max['coal-first-new'] = ramp_params[p3]
m.Rd_max['coal-first-new'] = ramp_params[p3]

for key in i_r_keys:
    m.hr[key] = hr_params[p4]

m.EF_CO2['coal-first-new'] = readData_det.EF_CO2['coal-first-new'] * EF_CO2_ratio[p5]    

#=================================end Parameter sweep =====================

#===================start set scenario ======================================
# m.L: load demand in region r in sub-period s of representative day d of year t (MW)
# m.cf: capacity factor of renewable generation cluster i in region r at sub-period s, of representative day d of r
#     year t (fraction of the nameplate capacity)
# m.P_fuel: price of fuel for generator cluster i in year t ($/MMBtu)
# m.tx_CO2: carbon tax in year t ($/kg CO2)
scenario_L = [0, 1]
scenario_cf = [0, 1]
scenario_P_fuel = ["L", "M", "H"]
scenario_tx_CO2 = ["L", "M", "H"]
s1, s2, s3, s4 = 0,0,0,0
for r in m.r:
	for stage in m.stages:
	    for t in t_per_stage[stage]:
	        for d in m.d:
	            for s in m.hours:
	                m.L[r, t, d, s] = readData_det.L_by_scenario[scenario_L[s1]][r, t, d, s]

for r in m.r:
	for stage in m.stages:
	    for t in t_per_stage[stage]:
	        for d in m.d:
	            for s in m.hours:
	                for rn in m.rn:
	                    if (rn, r) in rn_r:
	                        m.cf[rn, r, t, d, s] = readData_det.cf_by_scenario[scenario_cf[s2]][rn, r, t, d, s]

for stage in m.stages:
	for t in t_per_stage[stage]:
	    for th in th_generators:
	    	if stage == 1:
	    		m.P_fuel[th, t, stage] = readData_det.P_fuel_scenarios[th, t, stage, 'O']	
	    	else:
	        	m.P_fuel[th, t, stage] = readData_det.P_fuel_scenarios[th, t, stage, scenario_P_fuel[s3]]	                        

for stage in m.stages:
	for t in t_per_stage[stage + 1]:
		if stage == 1:
			m.tx_CO2[t, stage] = 0
		else:
			m.tx_CO2[t, stage] = readData_det.tx_CO2[t, scenario_tx_CO2[s4]]

#===================end set scenario ======================================






# # Add equality constraints (solve the full space)
# for stage in m.stages:
#     if stage != 1:
#         # print('stage', stage, 't_prev', t_prev)
#         for (rn, r) in m.rn_r:
#             m.Bl[stage].link_equal1.add(expr=(m.Bl[stage].ngo_rn_prev[rn, r] ==
#                                               m.Bl[stage-1].ngo_rn[rn, r, t_per_stage[stage-1][-1]] ))
#         for (th, r) in m.th_r:
#             m.Bl[stage].link_equal2.add(expr=(m.Bl[stage].ngo_th_prev[th, r] ==
#                                                 m.Bl[stage-1].ngo_th[th, r, t_per_stage[stage-1][-1]]  ))
#         for (j, r) in j_r:
#             m.Bl[stage].link_equal3.add(expr=(m.Bl[stage].nso_prev[j, r] ==
#                                                  m.Bl[stage-1].nso[j, r, t_per_stage[stage-1][-1]]))

#         for l in m.l_new:
#             m.Bl[stage].link_equal4.add(expr=(m.Bl[stage].nte_prev[l] ==
#                                                  m.Bl[stage-1].nte[l, t_per_stage[stage-1][-1]]))
# m.obj = Objective(expr=0, sense=minimize)

# for stage in m.stages:
#     m.Bl[stage].obj.deactivate()
#     m.obj.expr += m.Bl[stage].obj.expr


# # # solve relaxed model
# a = TransformationFactory("core.relax_integrality")
# a.apply_to(m)

# opt = SolverFactory("cplex")
# opt.options['mipgap'] = 0.01
# opt.solve(m, tee=True)


# variable_operating_cost = []
# fixed_operating_cost =[]
# startup_cost = []
# thermal_generator_cost = []
# extending_thermal_generator_cost = []
# renewable_generator_cost = []
# extending_renewable_generator_cost = []
# storage_investment_cost = []
# penalty_cost = []
# renewable_capacity = []
# thermal_capacity = []
# total_capacity = []
# transmission_line_cost = []
# for stage in m.stages:
#     variable_operating_cost.append(m.Bl[stage].variable_operating_cost.expr())
#     fixed_operating_cost.append(m.Bl[stage].fixed_operating_cost.expr())
#     startup_cost.append(m.Bl[stage].startup_cost.expr())
#     thermal_generator_cost.append(m.Bl[stage].thermal_generator_cost.expr())
#     extending_thermal_generator_cost.append(m.Bl[stage].extending_thermal_generator_cost.expr())
#     renewable_generator_cost.append(m.Bl[stage].renewable_generator_cost.expr())
#     extending_renewable_generator_cost.append(m.Bl[stage].extending_renewable_generator_cost.expr())
#     storage_investment_cost.append(m.Bl[stage].storage_investment_cost.expr())
#     penalty_cost.append(m.Bl[stage].penalty_cost.expr())
#     renewable_capacity.append(m.Bl[stage].renewable_capacity.expr())
#     thermal_capacity.append(m.Bl[stage].thermal_capacity.expr())
#     total_capacity.append(m.Bl[stage].total_capacity.expr())
#     transmission_line_cost.append(m.Bl[stage].transmission_line_cost.expr())

# print("variable_operating_cost")
# print(variable_operating_cost)
# print(sum(variable_operating_cost))
# print("fixed_operating_cost")
# print(fixed_operating_cost)
# print(sum(fixed_operating_cost))
# print("startup_cost")
# print(startup_cost)
# print(sum(startup_cost))
# print("thermal_generator_cost")
# print(thermal_generator_cost)
# print(sum(thermal_generator_cost))
# print("extending_thermal_generator_cost")
# print(extending_thermal_generator_cost)
# print(sum(extending_thermal_generator_cost))
# print("renewable_generator_cost")
# print(renewable_generator_cost)
# print(sum(renewable_generator_cost))
# print("extending_renewable_generator_cost")
# print(extending_renewable_generator_cost)
# print(sum(extending_renewable_generator_cost))
# print("storage_investment_cost")
# print(storage_investment_cost)
# print(sum(storage_investment_cost))
# print("penalty_cost")
# print(penalty_cost)
# print(sum(penalty_cost))
# print("renewable_capacity")
# print(renewable_capacity)
# print(sum(renewable_capacity))
# print("thermal_capacity")
# print(thermal_capacity)
# print(sum(thermal_capacity))
# print("total_capacity")
# print(total_capacity)
# print(sum(total_capacity))
# print("transmission_line_cost")
# print(transmission_line_cost)
# print(sum(transmission_line_cost))
