"""
    Documentar codigo con Docstring
    Path de este directorio /usr/local/airflow/dags/cel_afijo
    Path de la carpeta Ansible /urs/local/ansible/
"""
import json
import io
import sys 

hostname = str(sys.argv[1])
salida = json.load(open("/usr/local/tambo/files/cels/cel_afijo/tmp/json4db/"+hostname+"4db.json"))
lisyfinal = "/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/mongo/E6Kfinalisy_"+hostname+"_source.json"


infofinal = list(filter(lambda d: 'mgt' in d, salida))
infofinalup = list(filter(lambda d: 'up_slot' in d, infofinal))
infofinaldw = list(filter(lambda d: 'dw_slot' in d, infofinal))
print(infofinal)


dict = {}
salidalist = []

for item in infofinalup:
    for item2 in infofinaldw:
         if item['mgt'] == item2['mgt']:
            dict['dw_slot'] = item2['dw_slot']
            dict['dw_conn'] = item2['dw_conn']
            dict['up_slot'] = item['up_slot']
            dict['up_conn'] = item['up_conn']
            dict['mac_domain'] = item['mac_domain']
            dict['cmts'] = hostname
            salidalist.append(dict.copy())
            dict.clear()


with open(lisyfinal, "w") as out_file:
    json.dump(salidalist, out_file)
