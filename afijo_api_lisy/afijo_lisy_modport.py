from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from lisy_plugin.operators.lisy_operator import LisyCheckTokenOperator, LisyModPort, LisyQueryPort, LisyQueryOops, LisyQueryCorporateService
#from airflow.operators.postgres_operator import PostgresOperator
#from time import sleep
import os
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2020, 1, 1),
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

#tasks
# t0 = DummyOperator(task_id='inicio', retries=1, dag=dag)

# t1 = _q_port = LisyQueryPort(
#     task_id='query_port_ini',
#     params={
#     },
#     shelf_name = 'BEL1NA',
#     port_id = '0/10/1/5',
#     dest_dir = '/usr/local/airflow/reports/Lisy/',
#     dag=dag
# )

# t2 = _m_port = LisyModPort(
#             task_id='mod_port', 
#             shelf_name = 'BEL1NA',#otro: IC1.HOR1 - 9/0/1
#             port_id = '0/10/1/5',
#             info1 = 'Prueba Lucas',
#             dag=dag
#         ) 

# t3 = _q_port = LisyQueryPort(
#     task_id='query_port_end',
#     params={
#     },
#     shelf_name = 'BEL1NA',
#     port_id = '0/10/1/5',
#     dest_dir = '/usr/local/airflow/reports/Lisy/',
#     dag=dag
# )

# t0 >> t1 >> t2 >> t3



_q_port	= LisyQueryPort(
    task_id='query_port',
    shelf_name = 'LAC2MU',  
    port_id = '0/4/1/0',
    dest_dir = '/usr/local/airflow/reports/Lisy/',
    dag=dag
)



_m_port	= LisyModPort(
    task_id='mod_port', 
    Shelfname = 'LAC2MU',
    Port = '0/4/1/0',
    dest_dir = '/usr/local/airflow/reports/Lisy/',   
    info1 = 'Enlace 10G A COE1NA_Te0/11/0/4 (Linea:13006520) - UPLINK BBIP - Test',
    dag=dag
) 

_q_port1	= LisyQueryPort(
    task_id='query_port1', 
    shelf_name = 'LAC2MU',  
    port_id = '0/4/1/0',
    dest_dir = '/usr/local/airflow/reports/Lisy/',
    dag=dag
)





##################


_q_port >> _m_port >> _q_port1