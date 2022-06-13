# import defaults
import os
import shutil
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from teco_compliance.operators.TamboTCGComplianceOperator import TamboTCGComplianceOperator
import pymongo
from lib.teco_events import *
import glob

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'core',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['tambo_core@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}
            
#dag
dag = DAG(
dag_id= DAG_ID,
    schedule_interval = None, 
    #schedule_interval = "00 5 * * *", 
    default_args=default_args
)
            
#tasks
inicio = DummyOperator(task_id='dummy_task', retries=1, dag=dag)


def read_mongo(modelo=None):
    #HOST y PORT no cambia ya que es la mongo de TAMBO
    HOST = 'tambo_mongodb'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: forms
    mColForm = mDb["hostname"]

    result = [] 
    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        for equipos in mColForm.find({'ShelfNetworkRole':"HFC ACCESS", 'Modelo':modelo}):
            result.append(equipos['ShelfName'])
    except:
        result = ["Formulario sin registros"]
    print(result)
    return result

def render(equipo, modelo):
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/Misc_Secu_Mgm.tcg"
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    conf_file = f"*{equipo}.bkp"
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    dir_out = "/io/cel_core/compliance/afijo/resultados"
    owner = "AFIJO"

    MGMT_SECU_MISC = TamboTCGComplianceOperator(
        task_id='complianceMGMT_SECU_{}'.format(equipo),
        params={
            "file_tcg" : arch_template,              #// parametro obligatorio
            "dir_config" : w_dir,                    #// parametro obligatorio
            "file_config" : conf_file,               #// parametro obligatorio
            "dir_inv" : dir_json_inv,                #// parametro obligatorio
            "owner" : owner,                         #// parametro obligatorio
            "dir_sal" : dir_out,                     #// parametro opcional
            "NE" : equipo                            #// parametro opcional
            # "inventory_query" : inventory_query,   #// parametro opcional
            # "section" : "full",                    #// parametro opcional, se usa en conjunto con inventory_query
            # "debug_level" : 0                      #// parametro opcional - default = 0
        },
        dag=dag)

    return inicio >> MGMT_SECU_MISC


modelo = "CBR8"

equipos = read_mongo(modelo)
for equipo in equipos:
    origen = "/io/cel_core/backup/CMTS/"+equipo+"/configs/"
    archivos = glob.glob(origen+"*")
    if archivos:
        for archivo in archivos:
            src = origen + str(os.path.basename(archivo))
            dest = "/io/cel_core/compliance/afijo/configuraciones/" + str(os.path.basename(archivo))
            shutil.copyfile(src, dest)
        render(equipo,modelo)
