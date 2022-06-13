"""
Este DAG ...
"""

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
import os
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible
from teco_db.operators.tecoMongoDbOperator import TecoMongoDb


def test():
    pass


DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
# arg
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

# dag
dag = DAG(
    dag_id=DAG_ID,
    schedule_interval=None,
    default_args=default_args
)

# tasks
ini = DummyOperator(task_id='inicio', retries=1, dag=dag)

puertoscbr8  = _auto_ansible = tecoCallAnsible(
    task_id='puertoscbr8',
    op_kwargs={
        'Equipo_ONE': '*',
        'pbook_dir': '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/ansible',
        'playbook': 'afijo_PuertosCBR8.yaml',
        'connection': 'credenciales_equipos',
        'inventory': '/usr/local/airflow/dags/cel_afijo/inventory',
        'mock': False
    },
    dag=dag)

escribomongo = TecoMongoDb(
     task_id='Escribomongo',
     source_files='*',
     source_dir='/usr/local/tambo/cels/cel_afijo/airflow/dags/CompliancePuertosCMTS/output/mongo',
     table="CMTSCONFIG-Puertos",
     sorce_datatype='json',
     provide_context=False,
     dag=dag
 )

Compliance = _auto_ansible = tecoCallAnsible(
    task_id='comparacmts-lisy', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/ansible',
        'playbook':'afijo_compararCBR8.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
        'mock':False
    },
    dag=dag)

ini >> puertoscbr8 >> escribomongo >> Compliance