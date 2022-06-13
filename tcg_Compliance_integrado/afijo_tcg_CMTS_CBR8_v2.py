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
import json

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'aeaf',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['AFAutomation@teco.com.ar'],
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
inicio = DummyOperator(task_id='inicio', retries=1, dag=dag)

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
            #, 'ShelfName':"CMT1.AVA1-CBR8"
            result.append(equipos['ShelfName'])
    except:
        result = ["Formulario sin registros"]
    print(result)
    return result



def render_misc():
    datos = json.load(open("/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/datos.json"))
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_misc.tcg"
    dir_out = "/io/cel_core/compliance/afijo/resultados/misc"
    owner = "AFIJO"
    # debug_leve = "1"

    for x in datos:
        conf_file = str(x['file'])
        equipo = str(x['equipo'])
        compliance_misc = TamboTCGComplianceOperator(
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
        inicio >> compliance_misc
        compliance_misc.execute()
   
 
##############################################################################################

def render_int_cable_estaticas():
    datos = json.load(open("/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/datos.json"))
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    # arch_template = f"/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_{equipo}.tcg"
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_int_cable_estaticas.tcg"
    dir_out = "/io/cel_core/compliance/afijo/resultados/int_cable_estaticas/"
    owner = "AFIJO"

    for x in datos:
        conf_file = str(x['file'])
        equipo = str(x['equipo'])
        compliance_int_cable_estaticas = TamboTCGComplianceOperator(
            task_id='compliance_int_cable_estaticas{}'.format(equipo),
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
        inicio >> compliance_int_cable_estaticas
        compliance_int_cable_estaticas.execute()

##############################################################################################

def render_mgm():
    datos = json.load(open("/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/datos.json"))
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_mgm.tcg"
    dir_out = "/io/cel_core/compliance/afijo/resultados/mgm/"
    owner = "AFIJO"

    for x in datos:
        conf_file = str(x['file'])
        equipo = str(x['equipo'])
        compliance_mgm = TamboTCGComplianceOperator(
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
        inicio >> compliance_mgm
        compliance_mgm.execute()

####################################################################################################

def render_security():
    datos = json.load(open("/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/datos.json"))
    w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cisco_security.tcg"
    dir_out = "/io/cel_core/compliance/afijo/resultados/security/"
    owner = "AFIJO"

    for x in datos:
        conf_file = str(x['file'])
        equipo = str(x['equipo'])
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
        inicio >> compliance_security
        compliance_security.execute()


#######################################################################################################
def armo_json_copio_backups():
    modelo="CBR8"
    equipos = read_mongo(modelo)
    dict = {}
    salida = []
    for equipo in equipos:
        origen = "/io/cel_core/backup/CMTS/"+equipo+"/configs/"
        archivos = glob.glob(origen+"*")
        if len(archivos) > 0:
            ultimobackup = max(archivos, key=os.path.getctime)
            config = os.path.basename(ultimobackup)
            src = origen + str(os.path.basename(ultimobackup))
            dest = "/io/cel_core/compliance/afijo/configuraciones/" + str(os.path.basename(ultimobackup))
            shutil.copyfile(src, dest)
            dict['equipo'] = equipo
            dict['file'] = config
            salida.append(dict.copy())

    with open("/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/datos.json", "w") as outfile:
        json.dump(salida, outfile)

#######################################################################################################


_armo_json_copio_backups = PythonOperator(
    task_id='armo_json_copio_backups',
    python_callable=armo_json_copio_backups,
    provide_context=True,
    dag=dag 
    )  

_render_misc = PythonOperator(
    task_id='render_misc',
    python_callable=render_misc,
    provide_context=True,
    dag=dag 
    ) 

_render_int_cable_estaticas = PythonOperator(
    task_id='render_int_cable_estaticas',
    python_callable=render_int_cable_estaticas,
    provide_context=True,
    dag=dag 
    ) 

_render_mgm = PythonOperator(
    task_id='render_mgm',
    python_callable=render_mgm,
    provide_context=True,
    dag=dag 
    ) 

_render_security = PythonOperator(
    task_id='render_security',
    python_callable=render_security,
    provide_context=True,
    dag=dag 
    ) 



inicio >> _armo_json_copio_backups >> _render_misc
inicio >> _armo_json_copio_backups >> _render_int_cable_estaticas
inicio >> _armo_json_copio_backups >> _render_mgm
inicio >> _armo_json_copio_backups >> _render_security

