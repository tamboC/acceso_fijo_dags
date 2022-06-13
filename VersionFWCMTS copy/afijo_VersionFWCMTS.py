"""
Este DAG realiza el backup de los NE que esten dentro del inventario.
Los paramtros del operador tecoCallAnsible están documentados dentro del operador.
Los backups se guardan en la carpeta '/data/backup/'.
También es posible realizar un mock copiando en la carpeta backup los archivos testigos alojados en backup_mock.
"""

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
#from airflow.operators.postgres_operator import PostgresOperator
#from time import sleep
import os
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2020, 1, 1),
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

version_cbr8 = _auto_ansible = tecoCallAnsible(
    task_id='version_cbr8', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/VersionFWCMTS/ansible',
        'playbook':'afijo_versionCMTSCBR8.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)

version_e6k = _auto_ansible = tecoCallAnsible(
    task_id='version_e6k', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/VersionFWCMTS/ansible',
        'playbook':'afijo_versionCMTSE6K.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)

version_c100g = _auto_ansible = tecoCallAnsible(
    task_id='version_c100g', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/VersionFWCMTS/ansible',
        'playbook':'afijo_versionCMTSC100G.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)

ini >> version_cbr8
ini >> version_e6k
ini >> version_c100g