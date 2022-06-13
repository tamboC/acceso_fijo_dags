"""
    Documentar codigo con Docstring
    Path de este directorio /usr/local/airflow/dags/cel_afijo
    Path de la carpeta Ansible /urs/local/ansible/
"""
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from lisy_plugin.operators.lisy_operator import *
from datetime import datetime, timedelta
    

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'afijo',
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
    schedule_interval= None, 
    default_args=default_args)
            
#tasks
###################
def group(cmts, **kwargs):

    t1 = LisyQueryCustom(
        task_id='LisyQueryCombinaciones-{}'.format(cmts), 
        query_id = 'OcupacionRedHFC-VistaFisica',
        my_filter = '["","{}",""]'.format(cmts),
        dest_dir = '/io/cel_afijo/tmp/',
        file_name = '{}'.format(cmts),
        dag=dag
    )

    return t0 >> t1 
##################################
t0 = DummyOperator(task_id='dummy_task', retries=1, dag=dag)


########################
list_cmts = ['CMT4.ITU1-CBR8', 'CMT1.ALM1-E6K', 'CMT1.AVA1-CBR8']

for i in list_cmts:
    group(i)
