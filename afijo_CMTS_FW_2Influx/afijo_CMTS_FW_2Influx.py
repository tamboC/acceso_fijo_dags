"""
Levanto la info guardar por el DAG VersionFWCMTS y la empujo a la iflux para ser graficada en grafana
"""

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
#from airflow.operators.postgres_operator import PostgresOperator
#from time import sleep
from lib.L_teco_db import insert_influxdb
import os
from os import strerror
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible
import re

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

#Python Callables
###################
def ReadVersion(nombre):
        if nombre.endswith('E6K'):
            try:
                fs = open('/io/cel_core/backup/CMTS/'+nombre+'/configs/version/ARRIS_'+nombre+'.cfg','rt')
                print(nombre, "E6K")
                version = re.search('(CER_V[0-9]{2}.[0-9]{2}.[0-9]{2}.[0-9]{4})', fs.readline())
                print('version =', version.group(0))
                fs.close()

                data = {'cmts':nombre,'vendor':'ARRIS','modelo':'E6K','fw':version.group(0)}
                data_tag = {'cmts_tag':nombre,'vendor_tag':'ARRIS','modelo_tag':'E6K','fw_tag':version.group(0)}
                timestamp = datetime.now()
                insert_influxdb([
                            {
                            'measurement': 'cmts_fw',
                            'tags': data_tag,
                            'time': timestamp,
                            'fields':data
                            }
                            ],
                            'afijo')
            except IOError as e:
                print("Se produjo un error de E/S: ", strerr(e.errno))
        if nombre.endswith('CBR8'):
            try:
                fs = open('/io/cel_core/backup/CMTS/'+nombre+'/configs/version/CISCO_'+nombre+'.cfg','rt')
                print(nombre, "CBR8")
                version = re.search('[0-9][0-9].[0-9][0-9].[0-9][0-9][a-z]', fs.readline())
                print('version =', version.group(0))
                fs.close()

                data = {'cmts':nombre,'vendor':'CISCO','modelo':'CBR8','fw':version.group(0)}
                data_tag = {'cmts_tag':nombre,'vendor_tag':'CISCO','modelo_tag':'CBR8','fw_tag':version.group(0)}
                timestamp = datetime.now()
                insert_influxdb([
                            {
                            'measurement': 'cmts_fw',
                            'tags': data_tag,
                            'time': timestamp,
                            'fields':data
                            }
                            ],
                            'afijo')
            except IOError as e:
                print("Se produjo un error de E/S: ", strerr(e.errno))

        if nombre.endswith('C100G'):
            try:
                fs = open('/io/cel_core/backup/CMTS/'+nombre+'/configs/version/CASA_'+nombre+'.cfg','rt')
                print(nombre, "CASA")
                version = re.search('[0-9].[0-9].[0-9]', fs.readline())
                print('version =', version.group(0))
                fs.close()

                data = {'cmts':nombre,'vendor':'CASA','modelo':'C100G','fw':version.group(0)}
                data_tag = {'cmts_tag':nombre,'vendor_tag':'CASA','modelo_tag':'C100G','fw_tag':version.group(0)}
                timestamp = datetime.now()               
                insert_influxdb([
                            {
                            'measurement': 'cmts_fw',
                            'tags': data_tag,
                            'time': timestamp,
                            'fields':data
                            }
                            ],
                            'afijo')

            except IOError as e:
                print("Se produjo un error de E/S: ", strerr(e.errno))

        
    
#

#tasks
def group(cmts, **kwargs):

    checkversion = PythonOperator(
        task_id='pushversion'+cmts,
        python_callable=ReadVersion,
        op_kwargs={'nombre':cmts},
        provide_context = False,
        dag=dag
        )

    return ini >> checkversion
##################################
ini = DummyOperator(task_id='inicio', retries=1, dag=dag)


########################
list_cmts = ['CMT5.ALM1-CBR8', 'CMT6.DEV1-E6K', 'CMT1.JMA1-C100G']
#ist_cmts = ['CMT6.DEV1-E6K']

for i in list_cmts:
    group(i)

#CMT6.DEV1-E6K
#CMT5-ALM1-CBR8
#CMT1.JMA1-C100G