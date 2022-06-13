"""
    Documentar codigo con Docstring
    Path de este directorio /usr/local/airflow/dags/cel_afijo
    Path de la carpeta Ansible /urs/local/ansible/
"""
import json
import io
import sys
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
import os
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible
from teco_db.operators.tecoMongoDbOperator import TecoMongoDb
from airflow.operators.python_operator import PythonOperator

def test():
    pass


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
    default_args=default_args
)
    
#función para habilitar el código del DAG en Sphinx
#def doc_sphinx():
#    pass
            
#tasks
ini = DummyOperator(task_id='inicio', retries=1, dag=dag)

puertos_cbr8 = _auto_ansible = tecoCallAnsible(
    task_id='puertos_cbr8', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/ansible', 
        'playbook':'afijo_PuertosCBR8.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)


ini >> puertos_cbr8
