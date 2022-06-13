from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
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


#Python Callables
###################
def test(ansible_data, **kwargs):
    logging.info("Desde función process_output [test]:")
    logging.info(ansible_data)

def readFormio (**kwargs):

    dataForm = TAMBO.GetForms(DAG_ID)
    
    print (dataForm)


    scopesIPv4_64 = dataForm['scopesIPv4'][0]['url'].split("base64,")[1]
    scopesIPv4 = yaml.load(base64.b64decode(scopesIPv4_64).decode('ascii'))



    scopesIPv4["CM_PRIMARY"][0] = scopesIPv4["CM_PRIMARY"][0].split("/")
    scopesIPv4["CM_PRIMARY"][0][0] = scopesIPv4["CM_PRIMARY"][0][0].split(".")
    scopesIPv4["CM_PRIMARY"][0][0][3] = str(int(scopesIPv4["CM_PRIMARY"][0][0][3])+1)
    scopesIPv4["CM_PRIMARY"][0][0] = scopesIPv4["CM_PRIMARY"][0][0][0]+"."+scopesIPv4["CM_PRIMARY"][0][0][1]+"."+scopesIPv4["CM_PRIMARY"][0][0][2]+"."+scopesIPv4["CM_PRIMARY"][0][0][3]
    for item in ["CM", "MTA", "SIP", "no_compatibles", "FIBERTEL", "PRI_NAT44", "PRIVATE", "PROV", "DSG"]:
        if item in scopesIPv4.keys():
            for n in range(len(scopesIPv4[item])):
                scopesIPv4[item][n] = scopesIPv4[item][n].split("/")
                scopesIPv4[item][n][0] = scopesIPv4[item][n][0].split(".")
                scopesIPv4[item][n][0][3] = str(int(scopesIPv4[item][n][0][3])+1)
                scopesIPv4[item][n][0] = scopesIPv4[item][n][0][0]+"."+scopesIPv4[item][n][0][1]+"."+scopesIPv4[item][n][0][2]+"."+scopesIPv4[item][n][0][3]

    print ("contenido de archivo ", scopesIPv4)

    uri = "/usr/local/airflow/dags/cel_afijo/afijo_prueba_alta_cmts/ansible/vars/form_vars.yml"
    with open (uri, "r" ) as form_vars_yml:
        form_vars = yaml.safe_load(form_vars_yml.read())

    form_vars["scopes"] = scopesIPv4

    print (form_vars)

    uri = "/usr/local/airflow/dags/cel_afijo/afijo_prueba_alta_cmts/ansible/vars/form_vars.yml"
    with open (uri, "w" ) as form_vars_yml:
        yaml.dump(form_vars, form_vars_yml)
 #         form_vars = yaml.safe_load(form_vars_yml.read())    

def taskGenerateConfig(**kwargs):

    #filtro = { "ShelfName" : { "$in": datos['Equipo']} }

 #    data = {"ShelfNetworkRole": "FTTH ACCESS", "Vendor": "Nokia"}
    data = {'ShelfName':'CMT5.DEV1-E6K'}

    generateConfig = TamboAnsibleOperator(
        task_id='TestOperadorAnsible', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/afijo_prueba_alta_cmts/ansible',
        playbook='config_CBR8_day1.yml',
        connection='credenciales_equipos',
        mock=False,
        FILTRO_CUSTOM=data,
#        dict_extravars=comandos,
        process_output = test,
        dag=dag)

    generateConfig.execute()



###############DEF TASK

read_formio = PythonOperator(
    task_id='read_formio',
    python_callable=readFormio,
    provide_context=True,
    dag=dag 
    ) 

generate_config = PythonOperator(
    task_id='Generate_Configuration',
    python_callable=taskGenerateConfig,
    provide_context=True,
    dag=dag 
    ) 


###############CALL TASK
read_formio >> generate_config