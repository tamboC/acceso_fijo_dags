"""
Documentar codigo con Docstring
Path de este directorio /usr/local/airflow/dags/cel_[object Object]
Path de la carpeta Ansible /urs/local/ansible/
"""
import os
import telnetlib
import sys
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible
from airflow.operators.python_operator import PythonOperator

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
dag_id= DAG_ID, 
    schedule_interval= None, 
    tags=['REF'],
    default_args=default_args
)

def telnet(**kwargs):
    HOST = "181.88.69.10"
    HOST_NAME = "CLI1LSUP"
    user = "x304372"
    password = "c.H4rLY*Ec0"
    PROMPT =  b"<CLI1LSUP>"
    PROMPT_USER =  b"Username:"
    PROMPT_PASS =  b"Password:"
    COMMAND = "display clock"
    port = 23

    original_stdout = sys.stdout
    string_without_empty_lines = ""

    tn = telnetlib.Telnet()
    tn.open(HOST,port=port , timeout=1)
    tn.read_until(PROMPT_USER, 5)
    tn.write(user.encode() + b'\n')
    tn.read_until(PROMPT_PASS, 5)
    tn.write(password.encode() + b'\n')
    tn.read_until(PROMPT, 5)
    print("send command")
    tn.write((COMMAND + '\n').encode())
    data = tn.read_until(PROMPT, 5)
    tn.close()
    print(type(data))
    data = data.decode()
    print(data)

    with open('/io/cel_afijo/tmp/resultado_equipo_{}.txt'.format(HOST_NAME), 'w') as f:
        f.write(data)

ini = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

telnet_equipo = PythonOperator(
    task_id='Telnet',
    python_callable=telnet,
    dag=dag
    )
    
ini >> telnet_equipo

