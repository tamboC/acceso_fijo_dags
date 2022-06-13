import os, time
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from lib.teco_data_management import *
from teco_mae_operator.operators.tecoMaeOperator import TecoMaeOperator
from datetime import datetime, timedelta
from lib.L_teco_db import insert_influxdb


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

def gen_data(**kwargs):
    # print(today)

    start = 16
    stop = 238
    step = -2
    step2 = 2
    data = []
    for i in range(stop, start, step): 
    # for i in range(start, stop, step2): 
        timestamp = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        insert_influxdb([{
                    'measurement': 'prueba',
                    'tags': {
                            'central_name': 'Marce',
                            },
                    'time': timestamp,
                    'fields':{
                        'tempInt': int(i)
                    }
                }], 'afijo')

        # print(data)
        time.sleep(1)
    # for i in range(stop, start, step): 
    for i in range(start, stop, step2): 
        timestamp = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        insert_influxdb([{
                    'measurement': 'prueba',
                    'tags': {
                            'central_name': 'Lucas',
                            },
                    'time': timestamp,
                    'fields':{
                        'tempInt': int(i)
                    }
                }], 'afijo')

        # print(data)
        time.sleep(1)
    for i in range(stop, start, step): 
    # for i in range(start, stop, step2): 
        timestamp = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
        insert_influxdb([{
                    'measurement': 'prueba',
                    'tags': {
                            'central_name': 'Raul',
                            },
                    'time': timestamp,
                    'fields':{
                        'tempInt': int(i)
                    }
                }], 'afijo')

        # print(data)
        time.sleep(1)
    
    # insert_influxdb(data, 'afijo')

_resultados = PythonOperator(
    task_id='gen_data',
    python_callable = gen_data,
    dag=dag
)


_resultados