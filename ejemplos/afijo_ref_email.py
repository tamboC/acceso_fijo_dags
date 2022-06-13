import os, time
import logging
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.email_operator  import EmailOperator
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

#########################

def mi_send_mail(mails = [], subject = None, content = None, **context):
    
    email_op = EmailOperator(
                task_id='send_email',
                to = mails,
                subject = subject,
                html_content = content,
                files=None
            )
    email_op.execute(context)
    print("Se envió email")


def send_mail_custom(**context):

    mi_mail = ['lnirigoyen@teco.com.ar']
    mi_subject = "Email desde TAMBO desde CUSTOM"
    mi_content = "Email desde TAMBO desde CUSTOM"
    mi_send_mail(mi_mail, mi_subject, mi_content)
    



#########################
# Operador python que internamente ejecuta el operador EmailOperator pero permite editar las variables del mismo
#########################

_send_mail_custom = PythonOperator(
   task_id='send_email_custom',
   python_callable=send_mail_custom,
   provide_context=True,
   dag=dag
)

#########################
# Operador estatico para enviar mails como task 
#########################
_send_email_op = EmailOperator(
            task_id='send_email_op',
            to = "lnirigoyen@teco.com.ar",
            subject =  "Email desde TAMBO desde OPERADOR",
            html_content = "Email desde TAMBO desde OPERADOR",
            files= None,
            dag=dag
        )



#########################
_send_mail_custom >> _send_email_op