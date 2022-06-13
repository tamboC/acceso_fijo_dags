"""
Este Caso de Uso recompila la configuración de todos los equipos FTTH del parque de Telecom.
Hace uso del tecoCallAnsible2, en el ambiente productivo esta croneado para su ejecución a las 3am los dias 
Lunes, Miercoles y Viernes ('0 3 * * 1,3,5'). 
"""
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator_2 import tecoCallAnsible2


DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg


default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['cel_afijo@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}

#dag
dag = DAG(
    dag_id= DAG_ID, 
    schedule_interval= None, 
    tags=['BACKUP', 'FTTH'],
    default_args=default_args
)

####################################################
ini = DummyOperator(task_id= "Inicio", dag = dag)


backup_HW = tecoCallAnsible2(
        task_id='Backup_HW', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/BackupOLT/ansible',
        playbook='afijo_backupolt_hw_2.yaml',
        connection='credenciales_olt_hw',
        mock=False,
        FILTRO_CUSTOM={'ShelfNetworkRole' : "FTTH ACCESS", 'PrePro' : "True", 'Vendor' : "Huawei"},
        dag=dag)

backup_NK = tecoCallAnsible2(
        task_id='Backup_NK', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/BackupOLT/ansible',
        playbook='afijo_backupolt_nk_2.yaml',
        connection='credenciales_olt_nk',
        mock=False,
        FILTRO_CUSTOM={'ShelfNetworkRole' : "FTTH ACCESS", 'PrePro' : "True", 'Vendor' : "Nokia"},
        dag=dag)

ini >> backup_HW
ini >> backup_NK
