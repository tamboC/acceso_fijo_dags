"""
Este DAG realiza el backup de los NE que esten dentro del inventario.
Los paramtros del operador tecoCallAnsible están documentados dentro del operador.
Los backups se guardan en la carpeta '/data/backup/'.
También es posible realizar un mock copiando en la carpeta backup los archivos testigos alojados en backup_mock.

prueba
"""

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
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
t0 = DummyOperator(task_id='inicio', retries=1, dag=dag)

t1 = _auto_ansible = tecoCallAnsible(
    task_id='exec_ansible', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/afijo_prueba_conectividad_OLT',
        'playbook':'afijo_prueba_ansible_olt.yaml',
        'connection':'credenciales_olt_hw',
        'inventory':'/usr/local/airflow/dags/cel_afijo/afijo_prueba_conectividad_OLT/repository.yaml',
        'mock':False
    },
    dag=dag)

t0 >> t1
