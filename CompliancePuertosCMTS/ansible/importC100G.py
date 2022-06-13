import json
import sys

hostname = str(sys.argv[1])

armado = json.load(open("/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/C100G_"+hostname+"_source.json"))
upstream = json.load(open("/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/C100G_"+hostname+"_UP_source.json"))
final = "/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/mongo/C100Gagrego_"+hostname+"_source.json"

dict = {}
salidalist = []

for item in armado:
    for item2 in upstream:
         if item['up_slot'] == item2['up_slot'] and item['up_conn'] == item2['up_conn'] and item['up_chann'][0] == item2['up_chann']:
            dict['dw_slot'] = item['dw_slot']
            dict['dw_conn'] = item['dw_conn']
            dict['up_slot'] = item['up_slot']
            dict['up_conn'] = item['up_conn']
            dict['mac_domain'] = item['mac_domain']
            dict['power_up'] = item2['power_up']
            dict['cmts'] = hostname
            salidalist.append(dict.copy())
            dict.clear()

with open(final, "w") as out_file:
    json.dump(salidalist, out_file)