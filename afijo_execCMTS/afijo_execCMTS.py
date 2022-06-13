"""
Este DAG toma los equipos del inventario de Tambo y ejecuta los comandos ingresados
en el formulario.\n
"""

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
#from teco_ansible.operators.tecoAnsibleOperator_2 import tecoCallAnsible2
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator
from teco_db.operators.tecoMongoDbOperator import TecoReadMongo
from bson.objectid import ObjectId
from airflow.models import XCom

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")

#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['afautomation@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'max_active_runs': 1,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}

#dag
dag = DAG(
    dag_id=DAG_ID, 
    schedule_interval= None, 
    default_args=default_args,
    tags=['HFC']
)

# Funcion para parsear el submit de Formio

def datos_submit(**kwargs):
    datos={}
    
    id_submit=kwargs["dag_run"].conf.get("_id")
    # DEBUG, ver el filtro a utilizar
    #print (f"El id del submit es: {id_submit}")
    #importo de la mongo los datos insertados en el formularios por el usuario, usando el _id de submission
    data_submit = read_mongo(id_submit,"formio","submissions")[0]
    ##DEBUG##print(data_submit)

    datos['Equipo'] = data_submit.get('data').get('selectSomeCmts')
    datos['EquipoRegion'] = data_submit.get('data').get('selectCmtsRegion')
    datos['Modelo'] = data_submit.get('data').get('selectVendor')
    datos['Region'] = data_submit.get('data').get('selectRegion')
    datos['choice'] = data_submit.get('data').get('selectChoice')
    datos['choiceRegion'] = data_submit.get('data').get('choiceRegion')
    datos['preCommand'] = data_submit.get('data').get('commandPre').split('\n')
    datos['confCommand'] = data_submit.get('data').get('commandConf').split('\n')
    datos['postCommand'] = data_submit.get('data').get('commandPost').split('\n')

    kwargs["dag_run"].conf = {"comandos" : {"pre": datos['preCommand'], "conf": datos['confCommand'], "post" : datos['postCommand']}, "vendor": datos['Modelo']}
    return datos
    
def read_mongo(id_submit = None, db= None ,collection = None, host = 'tambo_mongodb', port = 27017)->list:
    mCli = pymongo.MongoClient(host,port)
    #SETEO la DB a USAR : formio
    mDb = mCli[db]
    #SETEO la colección: submissions
    mCollection = mDb[collection]
    
    data=[]

    if id_submit != None:
        try:
            for doc in mCollection.find({"_id":ObjectId(id_submit)}):
              data.append(doc)
            result = data
        except:
            result = data
    return result

# Creo el filtro para el operador Ansible 2
def filtro(**kwargs):
  comandos = kwargs["dag_run"].conf.get("comandos")
  vendor = kwargs["dag_run"].conf.get("vendor")
# DEBUG, ver el filtro a utilizar
  #print(comandos)
  #print(vendor)
  filtro = {}
  task_instance = kwargs['task_instance']
  datos = task_instance.xcom_pull(key='return_value', task_ids='datos_submit')
  if datos['choice'] == 'allCmts':
      filtro = {'Modelo' : datos['Modelo']}
  elif datos['choice'] == 'someCmts':
    filtro = { "ShelfName" : { "$in": datos['Equipo']} }
  elif datos['choice'] == 'someCmtsRegion':
    if datos['choiceRegion'] == 'allCmts':
      filtro =  { "$and" : [{'Modelo' : datos['Modelo']}, {'RegionName' : datos['Region']}] }
    elif datos['choiceRegion'] == 'someCmts':
      filtro = { "ShelfName" : { "$in": datos['EquipoRegion']} }
  kwargs["dag_run"].conf = {"filtro": filtro, "comandos" : comandos, "vendor" : vendor}
  #return filtro


def tarea_execute_playbook(**kwargs):
    # Obtengo el filtro y los comandos    
    data = kwargs["dag_run"].conf.get("filtro")
    comandos = kwargs["dag_run"].conf.get("comandos")
    vendor = kwargs["dag_run"].conf.get("vendor")
    
    # DEBUG, ver el filtro a utilizar
    #print(data)
    #print(comandos)
    #print(vendor)

    playbook=''
    if vendor == 'CBR8':
      playbook = 'afijo_execCBR8.yaml'
    elif vendor == 'E6000':
      playbook = 'afijo_execE6K.yaml'
    else:
      playbook = 'afijo_execC100G.yaml'

    #defino mi operador de ansible

    _test_operador_ansible = TamboAnsibleOperator(
    #_test_operador_ansible = tecoCallAnsible2(
        task_id='TestOperadorAnsible', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/afijo_execCMTS/ansible',
        playbook= playbook,
        connection='credenciales_equipos',
        mock=False,
        FILTRO_CUSTOM=data,
        dict_extravars= comandos,
        dag=dag)

  ##Ejecuto el operador de ansible
    _test_operador_ansible.execute()

#tasks

task_1 = PythonOperator(
   task_id='datos_submit',
   python_callable=datos_submit,
   provide_context=True,
   dag=dag
   )

task_2 = PythonOperator(
    task_id='filtro',
    python_callable=filtro,
    provide_context=True,
    dag=dag
    )

task_3 = PythonOperator(
    task_id='Exec_operador_ansible_by_py',
    python_callable=tarea_execute_playbook,
    provide_context=True,
    dag=dag 
    )   

task_1 >> task_2 >> task_3