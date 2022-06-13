from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta
from lib.tambo import *
import os
import sys
import pymongo
import json
from datetime import datetime, timedelta
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator
from teco_db.operators.tecoMongoDbOperator import TecoReadMongo
from bson.objectid import ObjectId
from airflow.models import XCom
import base64
import yaml 
import csv
import jinja2

from lib.L_afijo import *

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")

def test(context):
    print('success callback')
    
#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['afijo@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    #'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}

#dag
dag = DAG(
    dag_id= DAG_ID, 
    schedule_interval= None,
    tags=['CCAP'],
    default_args=default_args
)

#DEF METODOS
###################

class node:
    def __init__ (self, node_name ,ncp):
        self.dw_ch_map = "48"
        
        for r in ncp:
            if r[10] == node_name and r[4] == "UpStream" :
                print (r)
                self.node_name = r[10]
                self.up_controller = r[3]
                self.dw_controller = r[7]
                self.up_ch_map = r[9]
                aux = r[8].split(" ")
                self.up_power_level = int(aux[0])
                aux = r[3].split("/")
                self.up_linecard = int(aux[0])
                self.up_port = int(aux[2])
                aux = r[7].split("/")
                self.dw_linecard = int(aux[0])
                self.dw_port = int(aux[2])
            if r[10] == node_name and r[4] == "DownStream" :
                self.dw_ch_map = int(r[9])


#Python Callables
###################


def check_ne_inventory (**kwargs):
        ccap_to_config = kwargs["dag_run"].conf.get("ccap") 

        logging.info(f'cmts_to_config:{ccap_to_config}')
        #Datos para la funcion read_mongo_generic_find_one() --> Collection afijo_alta_olts
        db = 'tambo'
        collection='afijo_alta_cmts'
        filter = {'cmtsNombre':ccap_to_config}
        
        #Datos para la funcion read_mongo_generic_find_one() --> Collection hostname
        collection_hostname='hostname'
        filter_hostname = {'ShelfName': ccap_to_config}
        
        #Leo el CCAP desde la collection
        try:
            print('debug result find one')
            result_find_one = read_mongo_generic_find_one(db,collection,filter)
            print(result_find_one)
        except Exception as e:
            print(e)

        #Verifico que que la olt este en el inventario de Tambo para que funcione el filtro 
        result_find_one_hostname = read_mongo_generic_find_one(db,collection_hostname,filter_hostname)
        # print(result_find_one_hostname)
        dataCCAP = {}
        if (result_find_one_hostname is None):
            print('Se procedera a insertar el CCAP en el inventario de Tambo...')
            ccap_to_insert_inventory_tambo = {
                "IPName":result_find_one['cmtsLoopDirIPv4'],
                "IPSubnetMask":32,
                "BuildingName":None,
                "ShelfName":result_find_one['cmtsNombre'],
                "ShelfNetworkRole":"HFC ACCESS",
                "ShelfState":"Pre-Active",
                "RackName":None,
                "RoomName":None,
                "BuildingLongitude":None,
                "BuildingLatitud":None,
                "BuildingAddress":None,
                "RegionName":None,
                "Subregion":None,
                "NetworkElement":result_find_one['cmtsNombre'],
                "Vendor": 'Cisco',
                "Modelo": 'CBR8',
                "legacy":None,
                "LAB":"False",
                "PrePro":"True",
                "Prod":"True",
                "VersionFW":None,
                "VersionSW":None,
                "AccessTech":None,
                "Credenciales":None,
                "OperationalState del Shelf":None,
                "VARIABLES_CUSTOM":None,
                "ansible_network_os": "ios"}
            result_insert = insert_mongo_generic_insert_one(db,collection_hostname,ccap_to_insert_inventory_tambo)
            dataCcap = {"nameCcap" : result_find_one['cmtsNombre'],
                       "marcaCcap": result_find_one['vendor']
            }
            
            # if isinstance(result_insert,dict):
            #     dataOlt = result_insert
        else:
            print('El CMTS ya existe en el inv de Tambo')
            print(result_find_one_hostname)  
            #Armo el dict con la data a enviar a Ansible
            dataCcap = {"nameCcap" : result_find_one['cmtsNombre'],
                       "marcaCcap": result_find_one['vendor']
            }

        return dataCcap
        kwargs["dag_run"].conf.update({"dataCcap" : dataCcap})
        return dataCcap



def test(ansible_data, **kwargs):
    logging.info("Desde función process_output [test]:")
    logging.info(ansible_data)

def readFormio (**kwargs):

    debuging = True

    dataForm = TAMBO.GetForms(DAG_ID)
    
    logging.info (dataForm)


    combinations_64 = dataForm['combinaciones'][0]['url'].split("base64,")[1]
    combinations  = base64.b64decode(combinations_64).decode('ascii')

    ccap = dataForm.get('ccap')
    apply_config = dataForm['apply_config']
    vendor = dataForm['vendor']

    to_print = "CCAP a configurar: " + ccap
    logging.info (to_print)    
    to_print = "Vendor: " + vendor
    logging.info (to_print)    
    to_print = "Aplicar configuracion: " + str(apply_config)
    logging.info (to_print)    

#    job.log.info(form['data']['combinaciones'])    
#    port_parameters=form['data']['combinaciones']

#    log.info(json.dumps(form,indent=1))

#    job.log.info(data_file)
    
#    print ("#### CONTENIDO DEL ARCHIVO ####")
#    print (data_file)

    port_parameters = combinations



    port_parameters = port_parameters.split("\r\n")
    del port_parameters [-1]

    for i in range (0, len(port_parameters)):
        port_parameters[i] = port_parameters[i].split(";")

    kwargs["dag_run"].conf.update({"ccap" : ccap})
    kwargs["dag_run"].conf.update({"vendor" : vendor})
    kwargs["dag_run"].conf.update({"apply_config" : apply_config})    
    kwargs["dag_run"].conf.update({"port_parameters" : port_parameters})
    kwargs["dag_run"].conf.update({"debuging" : debuging})



def processCombinations(**kwargs):

    port_parameters = kwargs["dag_run"].conf.get("port_parameters") 
    cmts = kwargs["dag_run"].conf.get("ccap") 
    debuging = kwargs["dag_run"].conf.get("debuging") 
    vendor = kwargs["dag_run"].conf.get("vendor") 
    apply = kwargs["dag_run"].conf.get("apply_config") 

    nodes_list = list()
    for row in port_parameters:
        if row[1] == cmts :
            if (row[10] not in nodes_list) and (row[10]!= "" and  row[4] == "UpStream"):
                nodes_list.append(row[10])
    if debuging == True:
        print (nodes_list)
    combinaciones = dict()
    combinaciones["hostname"] = cmts
    combinaciones["apply_config"] = apply
    combinaciones["ports"] = list()

    for n in nodes_list:
        item = node(n, port_parameters)
        combinaciones["ports"].append({
        "name" : item.node_name,
        "upstream_controller" : item.up_controller,
        "linecard" : item.up_linecard,
        "up_port": item.up_port,
        "up_power_level" : item.up_power_level,
        "up_ch_map" : item.up_ch_map,
        "downstream_controller" : item.dw_controller,
        "dw_port" : item.dw_port,
        "dw_ch_map" : item.dw_ch_map
        })
    
    combinaciones["ports_shutdown"] = list ()
    for lc in range (1, 10):
        for prt in range (0, 16):
            flag_shutdown = True
            for item in combinaciones["ports"]:
                if (str(lc) + "/0/" + str(prt)) == item["upstream_controller"]:
                    flag_shutdown = False
            if flag_shutdown == True:
                combinaciones["ports_shutdown"].append(str(lc) + "/0/" + str(prt))
    logging.info ("Informacion de puertos a configurar: \n")
    logging.info (json.dumps(combinaciones,indent=1))
    file_name = '/io/cel_afijo/tmp/alta_cmts/'+vendor+'/'+cmts+'/combinations.yml'
    with open (file_name, "w") as combinations_yml:
        yaml.dump(combinaciones, combinations_yml)

def checkDirectory(**kwargs):
    ccap = kwargs["dag_run"].conf.get("ccap") 

    #filtro = { "ShelfName" : { "$in": datos['Equipo']} }

# #    data = {"ShelfNetworkRole": "FTTH ACCESS", "Vendor": "Nokia"}
    data = {'ShelfName': ccap}
#    data = {'ShelfName':'CMT4.ITU1-CBR8'}

    _check_directory = TamboAnsibleOperator(
        task_id='TestOperadorAnsible', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/afijo_prueba_alta_cmts/ansible',
        playbook='create_directory.yml',
        connection='credenciales_equipos',
        mock=False,
        FILTRO_CUSTOM=data,
#        dict_extravars=comandos,
        process_output = test,
        dag=dag)

    _check_directory.execute()

def configureTarget(**kwargs):

    ccap = kwargs["dag_run"].conf.get("ccap") 

    #filtro = { "ShelfName" : { "$in": datos['Equipo']} }

# #    data = {"ShelfNetworkRole": "FTTH ACCESS", "Vendor": "Nokia"}
    data = {'ShelfName': ccap}
#    data = {'ShelfName':'CMT4.ITU1-CBR8'}

    _configure_target = TamboAnsibleOperator(
        task_id='TestOperadorAnsible', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/afijo_prueba_alta_cmts/ansible',
        playbook='config_CBR8_day2.yml',
#        playbook='playbook-prueba.yml',
        connection='credenciales_equipos',
        mock=False,
        FILTRO_CUSTOM=data,
#        dict_extravars=comandos,
        process_output = test,
        dag=dag)

    _configure_target .execute()





###############DEF TASK

read_formio = PythonOperator(
    task_id='Read_Formio',
    python_callable=readFormio,
    provide_context=True,
    dag=dag 
    ) 


check_directory = PythonOperator(
    task_id='Check_Directory',
    python_callable=checkDirectory,
    provide_context=True,
    dag=dag 
    ) 

check_inventory = PythonOperator(
                                        task_id='Check_inventory',
                                        python_callable=check_ne_inventory,
                                        provide_context=True,
                                        dag=dag
                                        )

process_combinations = PythonOperator(
    task_id='Process_Combinations',
    python_callable=processCombinations,
    provide_context=True,
    dag=dag 
    ) 

configure_target = PythonOperator(
    task_id='Configure_Target',
    python_callable=configureTarget,
    provide_context=True,
    dag=dag 
    ) 

###############CALL TASK
#read_formio >> generate_config
#read_formio >> check_inventory >> process_combinations >> configure_target


read_formio >> check_inventory >> check_directory >> process_combinations >> configure_target