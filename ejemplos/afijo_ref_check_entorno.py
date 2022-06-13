"""
Ejemplo de metodo para obtener el entorno de ejecución de un dag
"""

import os,sys , time
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from lib.teco_data_management import *
from teco_mae_operator.operators.tecoMaeOperator import TecoMaeOperator
from datetime import datetime, timedelta


DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['afijo@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    #'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}
        
#dag
dag = DAG(
    dag_id= DAG_ID, 
    schedule_interval= None,
    tags=['REF'], 
    default_args=default_args
)

def get_env():
    # Get the list of user's environment variables
    env_var = dict(os.environ).get("FA_ENTORNO")
    # Print the list of user's environment variables
    print(f'Environment variable: {env_var}')
    
    data = {
        "name_env" : env_var,
        "ip_env": ""
    }

    if env_var == "fa-dev":
        data["ip_env"] = "10.247.2.44"  
    elif env_var == "fa-test":
        data["ip_env"] = "10.247.2.43"  
    elif env_var == "fa-prod":
        data["ip_env"] = "10.247.2.42" 

        
    return data 

_task1 = PythonOperator(
    task_id='get_env',
    python_callable = get_env,
    dag=dag
)

_task1

