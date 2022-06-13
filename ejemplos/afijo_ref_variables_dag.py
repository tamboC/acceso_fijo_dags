import os, time
import logging
import pprint
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from lib.teco_data_management import *
from teco_mae_operator.operators.tecoMaeOperator import TecoMaeOperator
from datetime import datetime, timedelta
from lib.tambo import TAMBO

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")

#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['afijo@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
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

############Variables Globales################################
VARIABLE_1 = {}

###############Metodo ########################################
def test_1(**kwargs):

    # id_submit=kwargs["dag_run"].conf.get("_id")
    # print (f"El id del submit es: {id_submit}")
    # data = TAMBO.GetForm(id_submit)

    data = TAMBO.GetForm(kwargs)

def test_2(**kwargs):
    logging.info('Hola')
    pass


###############operador#######################################

_task_1 = PythonOperator( task_id='task_1', python_callable=test_1, provide_context=True,dag=dag)
_task_2 = PythonOperator( task_id='task_2',python_callable=test_2,provide_context=True,dag=dag)


_task_1 >> _task_2




