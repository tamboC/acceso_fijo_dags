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

#Python Imports
import os, csv
from datetime import datetime, timedelta
from os import strerror
#Python Teco Imports
from lib.L_teco_db import insert_influxdb
#Operators Teco Imports
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible

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

#Python callable
def process_data(**kwargs):    
    with open('/io/cel_afijo/tmp/olt_models.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',')
        for row in spamreader:
            data = {'olt':row[0],'vendor':row[1],'modelo':row[2],'parche':row[3],'fw':row[4]}
            data_tag = {'olt_tag':row[0],'vendor_tag':row[1],'modelo_tag':row[2],'parche_tag':row[3],'fw_tag':row[4]}
            timestamp = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
            insert_influxdb([
                            {
                            'measurement': 'olt_sw',
                            'tags': data_tag,
                            'time': timestamp,
                            'fields':data
                            }
                            ],
                            'afijo')

#tasks
ini = DummyOperator(task_id='INICIO', retries=1, dag=dag)
end = DummyOperator(task_id='FIN', retries=1, dag=dag)

version_hw = tecoCallAnsible(
    task_id='version_hw', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/tambo/cels/cel_afijo/airflow/dags/afijo_OLT_FW/ansible',
        'playbook':'pb_OLT_FW_HW.yml',
        'connection':'credenciales_olt_hw',
        'inventory':'/usr/local/tambo/cels/cel_afijo/airflow/dags/inventory',
        'mock':False
    },
    dag=dag)

version_nk = tecoCallAnsible(
    task_id='version_nk', 
    op_kwargs={
        'Equipo_ONE':'*',
        'pbook_dir':'/usr/local/tambo/cels/cel_afijo/airflow/dags/afijo_OLT_FW/ansible',
        'playbook':'pb_OLT_FW_NK.yml',
        'connection':'credenciales_olt_nk',
        'inventory':'/usr/local/tambo/cels/cel_afijo/airflow/dags/inventory',
        'mock':False
    },
    dag=dag)

process_output = PythonOperator(
    task_id='process_data',
    python_callable=process_data,
    dag=dag
)


ini >> version_hw >> process_output >> end
ini >> version_nk >> process_output >> end
