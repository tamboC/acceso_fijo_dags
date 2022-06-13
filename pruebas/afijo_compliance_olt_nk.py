from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from lib.tambo import *
from lib.L_afijo import *
import os
import sys
import pymongo
import json
from datetime import datetime, timedelta
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator
from teco_db.operators.tecoMongoDbOperator import TecoReadMongo
from bson.objectid import ObjectId
from airflow.models import XCom

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
    tags=['REF', 'COMPLIANCE', 'FTTH'],
    default_args=default_args
)

###############DEF METODOS
def test(ansible_data, **kwargs):
    logging.info("Desde función process_output [test]:")
    logging.info(ansible_data)
    print(len(ansible_data))
    equipos = []
    for item in ansible_data:
        for key, value in item.items() :
            # print (key)
            equipos.append(key)
            try:
                if item[key]["data_vlan"][0]["data_vlan"] == "HSIv2":
                    print(f"El Equipo:{key} esta OK")
                else:
                    print(f"El Equipo:{key} esta NO-OK")
            except:
                    print(f"El Equipo:{key} esta NO-OK")
    # print(equipos)


def tarea_execute_playbook(**kwargs):

    comandos = {
        'mykey': ['info configure qos profiles ingress-qos','info configure vlan id 30']
    }

    data = {"ShelfNetworkRole": "FTTH ACCESS", "Vendor": "Nokia"}
    # data = {'ShelfName': "ALGP01"}

    _test_operador_ansible = TamboAnsibleOperator(
        task_id='TestOperadorAnsible', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/pruebas/ansible',
        playbook='playbook_nk_test.yml',
        connection='credenciales_olt_nk',
        mock=False,
        FILTRO_CUSTOM=data,
        dict_extravars=comandos,
        process_output = test,
        verbosity = 0,
        dag=dag)

    _test_operador_ansible.execute()



###############DEF TASK
task = PythonOperator(
    task_id='Exec_operador_ansible_by_py',
    python_callable=tarea_execute_playbook,
    provide_context=True,
    dag=dag 
    ) 


###############CALL TASK
task