"""
Documentar codigo con Docstring
Path de este directorio /usr/local/airflow/dags/cel_[object Object]
Path de la carpeta Ansible /urs/local/ansible/
prueba
"""

import os
import pprint
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from airflow.operators.python_operator import PythonOperator
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator


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
    tags=['BACKUP', 'HFC'],
    default_args=default_args
)

def limpio_backup():
    result = []
    dir_path = "/io/cel_core/backup/CMTS/"
    for root, dirs, files in os.walk(dir_path):
        for file in files:        
            if file.endswith('.bkp'):
                file_path = root+'/'+str(file)
                created = os.path.getctime(root+'/'+str(file))
                print("File creado:",datetime.fromtimestamp(created))
                if datetime.fromtimestamp(created)<(datetime.now() - timedelta(days=15)):
                    print(datetime.now()-datetime.fromtimestamp(created))
                    try:
                        print (f"Eliminamos el archivo {file_path} por ser mas antiguo que 15 dias")
                        os.remove(file_path)
                    except OSError as e:
                        print("Error: %s : %s" % (file_path, e.strerror))
                else:
                    pass

####################################################
ini = DummyOperator(task_id= "Inicio", dag = dag)

backup_C100G = TamboAnsibleOperator(
                        task_id ='Backup_C100G', 
                        pbook_dir = '/usr/local/airflow/dags/cel_afijo/BackupCMTS/ansible',
                        playbook = 'afijo_backupC100G2.yaml',
                        connection = 'credenciales_equipos',
                        init_output = '/io/cel_afijo/tmp/BackupCMTS/inventory.yml',
                        mock = False,
                        FILTRO_CUSTOM = {'ShelfNetworkRole' : "HFC ACCESS", 'Vendor' : "Casa Systems"},
                        dag = dag)

backup_E6K = TamboAnsibleOperator(
                        task_id='Backup_E6K', 
                        pbook_dir = '/usr/local/airflow/dags/cel_afijo/BackupCMTS/ansible',
                        playbook = 'afijo_backupE6K2.yaml',
                        connection = 'credenciales_equipos',
                        init_output = '/io/cel_afijo/tmp/BackupCMTS/inventory.yml',
                        mock = False,
                        FILTRO_CUSTOM = {'ShelfNetworkRole' : "HFC ACCESS", 'Vendor' : "ARRIS"},
                        dag = dag)

backup_CBR8 = TamboAnsibleOperator(
                        task_id='Backup_CBR8', 
                        pbook_dir = '/usr/local/airflow/dags/cel_afijo/BackupCMTS/ansible',
                        playbook = 'afijo_BackupCBR82.yaml',
                        connection = 'credenciales_equipos',
                        init_output = '/io/cel_afijo/tmp/BackupCMTS/inventory.yml',
                        mock = False,
                        FILTRO_CUSTOM = {'ShelfNetworkRole' : "HFC ACCESS", 'Vendor' : "Cisco"},
                        dag=dag)

_limpio_backup = PythonOperator(
    task_id='limpio_backup',
    python_callable=limpio_backup,
    provide_context=True,
    dag=dag 
    )  
ini >> backup_C100G >> _limpio_backup
ini >> backup_E6K >> _limpio_backup
ini >> backup_CBR8 >> _limpio_backup