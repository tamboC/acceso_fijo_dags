"""
    Documentar codigo con Docstring
    Path de este directorio /usr/local/airflow/dags/cel_afijo
    Path de la carpeta Ansible /urs/local/ansible/
"""
import os
import sys
import pymongo
from bson.objectid import ObjectId
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from teco_db.operators.tecoMongoDbOperator import TecoMongoDb
from lisy_plugin.operators.lisy_operator import *
from datetime import datetime, timedelta


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
    default_args=default_args)

#Functions 
###################
def read_mongo(id_submit = None, name_form = None ,db= None ,collection = None, host = None, port = 27017):
    mCli = pymongo.MongoClient(host,port)
    #SETEO la DB a USAR : formio
    mDb = mCli[db]
    #SETEO la colección: submissions
    mCollection = mDb[collection]
    
    data=[]

    if id_submit != None and name_form == None:
        try:
            #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
            for doc in mCollection.find({"_id":ObjectId(id_submit)}):
              data.append(doc)  
            result = data
        except:
            result = data
    
    if id_submit == None and name_form != None:
        try:
            #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
            for doc in mCollection.find({"title": name_form}):
              data.append(doc)  
            result = data
        except:
            result = data

    print(result)
    return  result

def main(**kwargs):
    id_submit=kwargs["dag_run"].conf.get("_id")
    print (f"El id del submit es: {id_submit}")
    #importo de la mongo los datos insertados en el formularios por el usuario, usando el _id de submission
    data_submit = read_mongo(id_submit=id_submit,name_form=None,db="formio",collection="submissions",host="tambo_mongodb")




#Python Callables
###################

def leer_formio(**kwargs):
    log = TAMBO.GetForms(DAG_ID)
    print (log)

"""
def leer_formio(**kwargs):
    
    id_submit=kwargs["dag_run"].conf.get("_id")
    ##DEBUG## print (f"El id del submit es: {id_submit}")
    #importo de la mongo los datos insertados en el formularios por el usuario, usando el _id de submission
    data_submit = read_mongo(id_submit,"formio","submissions")[0]
    ##DEBUG##print(data_submit)

    ccap = data_submit.get('data').get('ccap')
    print (ccap)

    return True
"""

#tasks
###################
ini = DummyOperator(task_id='inicio', retries=1, dag=dag)

leer_formio = PythonOperator(
   task_id='leer_formio',
   python_callable=main,
   provide_context=True,
   dag=dag
   )

ini >> leer_formio