"""
Documentar codigo con Docstring
Hola
"""
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible
from datetime import datetime, timedelta

#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['celongo@teco.com.ar'],
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
dag_id= "afijo_Conectividad_CMTS", 
    schedule_interval= None, 
    default_args=default_args
)

def get_dir(**kwargs):
    path = "/usr/local/ansible/afijo/"
    file = "my_inventory"
    fp = open(file,'w')
    fp.write("[CMTS]\n10.100.153.30")
    fp.close()

    # inventory='/usr/local/ansible/inventario/inventario_ansible_host'
    # fp=open(inventory,'r')
    # content=fp.read()
    # fp.close()
    # print(content)
        
#tasks
t0 = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

t1 = PythonOperator(
    task_id = 'get_dir',
    python_callable=get_dir,
    dag=dag
)

t2 = tecoCallAnsible(
    task_id='exec_ansible', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/ansible/afijo_prueba_conectividad_CMTS',
        'playbook':'afijo_afijo_prueba_conectividad_CMTS.yaml',
        'connection':'credenciales_equipos',
        'inventory':'/usr/local/ansible/afijo/my_inventory',
        'mock':False
    },
    dag=dag)

t0 >> t1 >> t2