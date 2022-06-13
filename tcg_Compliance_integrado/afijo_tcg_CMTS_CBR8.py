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
        for equipos in mColForm.find({'ShelfNetworkRole':"HFC ACCESS", 'Modelo':modelo, 'ShelfName':"CMT1.AVA1-CBR8"}):
            result.append(equipos['ShelfName'])
    except:
        result = ["Formulario sin registros"]
    print(result)
    return result



def render_misc(equipo, modelo):
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_misc.tcg"
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    conf_file = config
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    dir_out = "/io/cel_core/compliance/afijo/resultados/misc"
    owner = "AFIJO"
    debug_leve = "1"

    compliance_misc = TamboTCGComplianceOperator(
        task_id='compliance_misc_{}'.format(equipo),
        params={
            "file_tcg" : arch_template,              #// parametro obligatorio
            "dir_config" : w_dir,                    #// parametro obligatorio
            "file_config" : conf_file,               #// parametro obligatorio
            "dir_inv" : dir_json_inv,                #// parametro obligatorio
            "owner" : owner,                         #// parametro obligatorio
            "dir_sal" : dir_out,                     #// parametro opcional
            "NE" : equipo,                            #// parametro opcional
            # "inventory_query" : inventory_query,   #// parametro opcional
            # "section" : "full",                    #// parametro opcional, se usa en conjunto con inventory_query
            #"debug_level" : debug_leve                      #// parametro opcional - default = 0
        },
        dag=dag)

    return inicio >> compliance_misc

##############################################################################################

def render_int_cable(equipo, modelo):
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    conf_file = config
    #conf_file = "CISCO_CMT5-ALM1-CBR8bis.config"
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    #arch_template = f"/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_{equipo}.tcg"
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_int_cable_estaticas.tcg"
    dir_out = "/io/cel_core/compliance/afijo/resultados/int_cable_estaticas/"
#    inventory_query = ""
    owner = "AFIJO"

    compliance_int_cable_estaticas = TamboTCGComplianceOperator(
        task_id='compliance_int_cable_estaticas_{}'.format(equipo),
        params={
            "file_tcg" : arch_template,
            "dir_config" : w_dir,
            "file_config" : conf_file,
            "dir_inv" : dir_json_inv,
            "dir_sal" : dir_out,
            "NE" : equipo,
            "owner" : owner
        },
        dag=dag)
    return inicio >> compliance_int_cable_estaticas

##############################################################################################

def render_mgm(equipo, modelo):
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    conf_file = config
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_mgm.tcg"
    dir_out = "/io/cel_core/compliance/afijo/resultados/mgm/"
    owner = "AFIJO"

    compliance_mgm = TamboTCGComplianceOperator(
        task_id='compliance_mgm_{}'.format(equipo),
        params={
            "file_tcg" : arch_template,
            "dir_config" : w_dir,
            "file_config" : conf_file,
            "dir_inv" : dir_json_inv,
            "dir_sal" : dir_out,
            "NE" : equipo,
            "owner" : owner
        },
        dag=dag)
    return inicio >> compliance_mgm

####################################################################################################

def render_security(equipo, modelo):
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    conf_file = config
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_security.tcg"
    dir_out = "/io/cel_core/compliance/afijo/resultados/security/"
    owner = "AFIJO"

    compliance_security = TamboTCGComplianceOperator(
        task_id='compliance_security_{}'.format(equipo),
        params={
            "file_tcg" : arch_template,
            "dir_config" : w_dir,
            "file_config" : conf_file,
            "dir_inv" : dir_json_inv,
            "dir_sal" : dir_out,
            "NE" : equipo,
            "owner" : owner
        },
        dag=dag)
    return inicio >> compliance_security

#######################################################################################################

modelo = "CBR8"

equipos = read_mongo(modelo)
for equipo in equipos:
    origen = "/io/cel_core/backup/CMTS/"+equipo+"/configs/"
    archivos = glob.glob(origen+"*")
    if len(archivos) > 0:
        ultimobackup = max(archivos, key=os.path.getctime)
        config = os.path.basename(ultimobackup)
        src = origen + str(os.path.basename(ultimobackup))
        dest = "/io/cel_core/compliance/afijo/configuraciones/" + str(os.path.basename(ultimobackup))
        shutil.copyfile(src, dest)
    render_misc(equipo,modelo)
    render_int_cable(equipo,modelo)
    render_mgm(equipo,modelo)
    render_security(equipo,modelo)
