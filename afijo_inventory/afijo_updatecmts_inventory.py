import os
import sys
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from teco_db.operators.tecoMongoDbOperator import TecoMongoDb
from lisy_plugin.operators.lisy_operator import *
from datetime import datetime, timedelta
import pymongo
    

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
    dag_id= 'afijo_update_inventory', 
    schedule_interval= None, 
    default_args=default_args
)

def update_inventory(**kwargs)->dict:
    HOST = '10.247.2.42'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    mDb = mCli["tambo"]
    mCollection = mDb["hostname"] 
    filtro = {'ShelfNetworkRole':{'$regex':'^HFC'}}
    data_update = {'$set': {'ansible_network_os': 'ios'}}
    try:
        result = mCollection.update_many(filtro, data_update)
        print(result.matched_count)
    except:
        result = "Error de update"


inicio = DummyOperator(task_id='inicio', retries=1, dag=dag)

update = PythonOperator(
task_id='update',
python_callable=update_inventory,
#op_kwargs={'dest_dir':'/io/cel_afijo/tmp/', 'file_name':cmts, 'shutdown':True},
provide_context = true,
dag=dag
)


inicio >> update