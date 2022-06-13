import os, time
import logging
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from lib.teco_data_management import *
from teco_mae_operator.operators.tecoMaeOperator import TecoMaeOperator
from datetime import datetime, timedelta
from teco_ansible.operators.tecoAnsibleOperator_2 import tecoCallAnsible2

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

##############################################################
#METODOS o FUNCIONES
##############################################################

def mi_filtro():
    #este metodo funciona mientras no tenga que interactuar con variables del DAG
    data = {'ShelfNetworkRole' : "FTTH ACCESS", 'PrePro' : "True", 'Vendor' : "Huawei"}
    return data


def tarea_execute_playbook(**context):
    #Leo un dato enviado externamente 
    data =context["dag_run"].conf.get("data")
    print (data)
    #Armo el filtro que necesito para ejecutar mi playbook
    valor = {'ShelfNetworkRole' : data, 'PrePro' : "True", 'Vendor' : "Huawei"}
    print(valor)

    #defino mi operador de ansible
    _test_operador_ansible = tecoCallAnsible2(
        task_id='TestOperadorAnsible', 
        pbook_dir='/usr/local/airflow/dags/cel_afijo/ejemplos/ansible',
        playbook='afijo_backupolt_hw_2.yaml',
        connection='credenciales_olt_hw',
        mock=False,
        FILTRO_CUSTOM=valor,
        dag=dag)

    #Ejecuto el operador de ansible
    print("ejecuto operador con variables")
    print(context)

    _test_operador_ansible.execute()

#############################################################
#OPERADORES
#############################################################

_exec_operador_ansible_by_py = PythonOperator(
            task_id='Exec_operador_ansible_by_py',
            python_callable=tarea_execute_playbook,
            provide_context=True,
            dag=dag 
            )    


# _operador_ansible = tecoCallAnsible2(
#         task_id='TestOperadorAnsible', 
#         pbook_dir='/usr/local/airflow/dags/cel_afijo/ejemplos/ansible',
#         playbook='afijo_backupolt_hw_2.yaml',
#         connection='credenciales_olt_hw',
#         #inventory='/usr/local/airflow/dags/cel_core/INFORME_MANONI/input/inventory_tambo_MANONI',
#         mock=False,
#         FILTRO_CUSTOM=mi_filtro(),
#         dag=dag)



#########################################################
#FLOW DE TRABAJO
#########################################################

# _operador_ansible

_exec_operador_ansible_by_py

