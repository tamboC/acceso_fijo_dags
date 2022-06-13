import json
import csv
import io
import sys


hostname = str(sys.argv[1])
#hostname = str("CMT1.ALM1-E6K")

#armado = json.load(open("/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/output/E6K_{{nombre}}_source.json")) 
dw = json.load(open("/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/E6K_"+hostname+"_sourcedw.json"))
dwe = json.load(open("/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/E6K_"+hostname+"_sourcedw.json"))
finaldw = "/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/mongo/finaldw_"+hostname+".json"
finalmac = "/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/mongo/mac_"+hostname+".json"
#final = "/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/output/E6Kagrego_{{nombre}}_source.json"



dict = {}
salidalist = []
resultantList = []


for item in dw:
    for item2 in dwe:
         if item['mac'] == item2['mac']:
             if item['freq_cen'] != item2['freq_cen']:
                     dict['freq_cen'] = item2['freq_cen']
                     dict['interface'] = item2['interface']
                     dict['mac'] = item2['mac']
                     dict['high_freq'] = item2['high_freq']
                     #if item['high_freq'] != '':
                     #      dict['high_freq'] = item2['high_freq']
                     salidalist.append(dict.copy())
                     dict.clear()


for element in salidalist:
    if element not in resultantList:
        resultantList.append(element)


dicmac = {}
listmac = []

for i in resultantList:
    dicmac['mac'] = i['mac']
    listmac.append(dicmac.copy())
    dicmac.clear()

#print (listmac)

salidalist1 = []
resultantList1 = []

for element in listmac:
    if element not in resultantList1:
        resultantList1.append(element)

print(resultantList1)


with open(finaldw, "w") as out_file:
    json.dump(resultantList, out_file)

with open(finalmac, "w") as out_file:
    json.dump(resultantList1, out_file)    