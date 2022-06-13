import json
import sys

cmts = str(sys.argv[1])
#file_name = "backup_"+ cmts + ".txt"
#file_name = "/home/coder/project/io/cel_core/backup/CMTS/"+cmts+"/configs/CISCO_CMT5.ALM1-CBR8_21-11-17.bkp"
file_name = "/usr/local/tambo/files/cels/cel_core/backup/CMTS/"+cmts+"/configs/CISCO_"+cmts+"_21-11-24.bkp"

print (file_name)
with open (file_name, "r") as backup_config_file:
	backup_config = backup_config_file.read()

#print (type(backup_config))
#print (len(backup_config ))

fiber_node = backup_config.split("fiber-node")

fiber_node = fiber_node [1:]

for i in range (len(fiber_node)):
	fiber_node[i] = fiber_node[i].split("\n")
	fiber_node[i] = fiber_node [i][0:3]
	fiber_node[i][0] = fiber_node[i][0].lstrip()
	fiber_node[i][1] = fiber_node[i][1].replace(" downstream Integrated-Cable ", "")
	fiber_node[i][2] = (fiber_node[i][2].replace(" upstream Upstream-Cable ", "")).rstrip()
#for row in fiber_node:
#	print (row)

up_controller = backup_config.split("controller Upstream-Cable")
del (up_controller [0])
#	del (up_controller [-1])
for i in  range (len (up_controller)):
	up_controller[i] = up_controller[i].split(" us-channel 0 docsis-mode atdma")
	up_controller[i] = up_controller[i][0]
	up_controller[i] = up_controller[i].split("\n")
	up_controller[i] = up_controller[i][0::3]
	up_controller[i][0] = up_controller[i][0].lstrip()
	up_controller[i][1] = up_controller[i][1].replace(" us-channel 0 power-level ", "")
#for row in up_controller:#
#	print (row) 	

for r in range(len (fiber_node)):
	for q in range(len(up_controller)):
		if fiber_node[r][2] == up_controller[q][0]:
			fiber_node[r].append(up_controller[q][1])

list_source = list()
dic_source = dict()		

for row in fiber_node:
#	print (row)
	dic_source["up_power"] = row [3]
	aux = row[2].split("/")
	dic_source["up_slot"] = aux [0]
	dic_source["up_conn"] = aux [2]
	dic_source["dw_slot"] = row [1]	
	dic_source["mac_domain"] = row [1]
	dic_source["cmts"] = cmts
	list_source.append(dic_source)

file_name = "CBR_" +cmts + "_source.json"
file_name = "/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/output/CBR8_"+cmts+"_source.json"
with open (file_name, "w") as f:
	json.dump (list_source, f )
