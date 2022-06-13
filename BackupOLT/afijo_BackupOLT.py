"""
Documentar codigo con Docstring
Path de este directorio /usr/local/airflow/dags/cel_[object Object]
Path de la carpeta Ansible /urs/local/ansible/
prueba
"""
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible

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

ini = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

backup_MA5800 = _auto_ansible = tecoCallAnsible(
    task_id='backup_HW', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/BackupOLT/ansible',
        'playbook':'afijo_backupolt_hw.yaml',
        'connection':'credenciales_olt_hw',
        # 'inventory':'/usr/local/airflow/test_ansible/inventario_olts',
        'inventory':'/usr/local/tambo/cels/cel_afijo/airflow/dags/BackupOLT/ansible/inventory',
        'mock':False
    },
    dag=dag)
    
backup_NK = _auto_ansible = tecoCallAnsible(
    task_id='backup_NK', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/BackupOLT/ansible',
        'playbook':'afijo_backupolt_nk.yaml',
        'connection':'credenciales_olt_nk',
        # 'inventory':'/usr/local/airflow/test_ansible/inventario_olts',
        'inventory':'/usr/local/tambo/cels/cel_afijo/airflow/dags/BackupOLT/ansible/inventory',
        'mock':False
    },
    dag=dag)


ini >> backup_MA5800
ini >> backup_NK
