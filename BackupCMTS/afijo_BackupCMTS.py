"""
Este DAG realiza el backup de los CMTS que esten dentro del inventario.\n
Los parametros del operador tecoCallAnsible están documentados dentro del operador.\n
Los backups se guardan en la carpeta '/usr/local/backup/CMTS/{{nombre_cmts}}/configs/'.\n
"""

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
import os
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible

def test():
    pass

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 9, 8),
    'email': ['automation@teco.com.ar'],
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
    dag_id=DAG_ID, 
    schedule_interval= None, 
    default_args=default_args
)

#tasks
ini = DummyOperator(task_id='inicio', retries=1, dag=dag)

backup_cbr8 = _auto_ansible = tecoCallAnsible(
    task_id='backup_cbr8', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/BackupCMTS/ansible',
        'playbook':'afijo_BackupCBR8.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)

backup_e6k = _auto_ansible = tecoCallAnsible(
    task_id='backup_e6k', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/BackupCMTS/ansible',
        'playbook':'afijo_BackupE6K.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)

backup_c100g = _auto_ansible = tecoCallAnsible(
    task_id='backup_c100g', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/BackupCMTS/ansible',
        'playbook':'afijo_BackupC100G.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)

ini >> backup_cbr8
ini >> backup_e6k
ini >> backup_c100g