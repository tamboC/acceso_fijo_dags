import json
import csv
import io
import sys


hostname = str(sys.argv[1])
#hostname = str("CMT1.ALM1-E6K")

#armado = json.load(open("/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/output/E6K_{{nombre}}_source.json")) 
armado = json.load(open("/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/E6K_"+hostname+"_source.json"))
final = "/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/mongo/E6Kagrego_"+hostname+"_source.json"
#final = "/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/output/E6Kagrego_{{nombre}}_source.json"

#for item in armado:
#    item.update({'CMTS': hostname})


interface_dict = {}

def SplitInterface(pasado):
    interface = pasado.split("/")
    if pasado == "":
         interface_dict['dw_slot'] = ""
         interface_dict['dw_conn'] = ""
    else: 
         interface_dict['dw_slot'] = interface[0]
         interface_dict['dw_conn'] = interface[1] 
    return interface_dict


coleccion = []
documento = {}
for i in armado:
    interface = SplitInterface(i['dw_slot'])
    documento['dw_slot'] = interface['dw_slot']
    documento['dw_conn'] = interface['dw_conn']
    print(interface['dw_slot'])
    print(interface['dw_conn'])
    documento['CMTS'] = hostname
    documento['mac_domain'] = i['mac_domain']
    documento['up_power'] = i['up_power']
    documento['up_slot'] = i['up_slot']
    documento['up_conn'] = i['up_conn']
    documento['frequency'] = i['frequency']
    documento['interface'] = i['interface']
    interface = SplitInterface(i['interface'])
    documento['up_slot'] = interface['dw_slot']
    documento['BW'] = i['BW']
    documento['profile'] = i['profile']
    coleccion.append(documento.copy())
    documento.clear()



coleccion.pop()
with open(final, "w") as out_file:
    json.dump(coleccion, out_file)