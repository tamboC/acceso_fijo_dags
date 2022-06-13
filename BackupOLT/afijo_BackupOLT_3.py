"""
Este Caso de Uso recompila la configuración de todos los equipos FTTH del parque de Telecom.
Hace uso del tecoCallAnsible2, en el ambiente productivo esta croneado para su ejecución a las 3am los dias 
Lunes, Miercoles y Viernes ('0 3 * * 1,3,5'). 
"""
import os, time, datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator
from airflow.operators.python_operator import PythonOperator

# from deepdiff import DeepDiff  # For Deep Difference of 2 objects
# from deepdiff import grep, DeepSearch  # For finding if item exists in an object
# from deepdiff import DeepHash  # For hashing objects based on their contents


DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg


default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2022, 1, 28),
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
    schedule_interval= ('0 3 * * 1,3,5'), 
    tags=['BACKUP', 'FTTH'],
    default_args=default_args
)
    
####################################################
def limpio_backup():
    result = []
    dir_path = "/io/cel_core/backup/OLT/"
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
_ini = DummyOperator(task_id= "Inicio", dag = dag)
_end = DummyOperator(task_id= "Fin", dag = dag)

_backup_HW = TamboAnsibleOperator(
        task_id='Backup_HW', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/BackupOLT/ansible',
        playbook='afijo_backupolt_hw_2.yaml',
        connection='credenciales_olt_hw',
        mock=False,
        FILTRO_CUSTOM={'ShelfNetworkRole' : "FTTH ACCESS", 'Vendor' : "Huawei"},
        dag=dag)

_backup_NK = TamboAnsibleOperator(
        task_id='Backup_NK', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/BackupOLT/ansible',
        playbook='afijo_backupolt_nk_2.yaml',
        connection='credenciales_olt_nk',
        mock=False,
        FILTRO_CUSTOM={'ShelfNetworkRole' : "FTTH ACCESS", 'Vendor' : "Nokia"},
        dag=dag)

_limpio_backup = PythonOperator(
    task_id='limpio_backup',
    python_callable=limpio_backup,
    provide_context=True,
    dag=dag 
    )  

_ini >> _backup_HW >> _limpio_backup >> _end
_ini >> _backup_NK >> _limpio_backup >> _end