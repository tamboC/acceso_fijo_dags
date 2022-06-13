"""
Documentar codigo con Docstring
Path de este directorio /usr/local/airflow/dags/cel_[object Object]
Path de la carpeta Ansible /urs/local/ansible/
"""
import os
import json
import pymongo
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from airflow.operators.python_operator import PythonOperator
from lib.tambo import *

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
    'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}

#dag
dag = DAG(
    dag_id= DAG_ID, 
    schedule_interval= None,
    tags = ['REF'],
    default_args=default_args
)


def read_mongo(**kwargs):
    #HOST y PORT no cambia ya que es la mongo de TAMBO
    HOST = 'tambo_mongodb'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: forms
    mColForm = mDb["forms"]
    
    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        x = mColForm.find_one({'title':"inventario_cmts"})
        filter={'form': (x['_id'])}
        print(filter)
        sort=list({'_id': -1}.items())
        limit=1
        result = []
        #Recorro el resultado de los documentos dentro de la colección aplicando el filtro
        for item in mCli['formio']['submissions'].find(filter=filter):
            print(item['data'])
            result.append(item['data'])
    except:
        result = ["Formulario sin registros"]

    print(result)

def insert_mongo(**kwargs):
   
    #HOST y PORT no cambia ya que es la mongo de TAMBO
    HOST = 'tambo_mongodb'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: forms
    mColForm = mDb["forms"]

    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        x = mColForm.find_one({'title':"inventario_cmts"})
        id_resource= x['_id']
        id_owner = x['owner']
                
        #Recorro el resultado de los documentos dentro de la colección aplicando el filtro
        mCli['formio']['submissions'].insert_one(
            {
                "owner": id_owner,
                "data": {
                        "nombreCmts": "CMT2.LUC1-LUC",
                        "vendorCmts": "LUC"
                    },
                "form": id_resource
            }
        )
        result = "Dato insertado"
    except:
        result = "error al insertar dato"
    print(result)

def update_mongo(**kwargs):
   
    #HOST y PORT no cambia ya que es la mongo de TAMBO
    HOST = 'tambo_mongodb'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: forms
    mColForm = mDb["forms"]

    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        x = mColForm.find_one({'title':"inventario_cmts"})
        id_resource= x['_id']
        id_owner = x['owner']
        #{'form': ObjectId('61705245b9fe55495996b182')}        
        #Recorro el resultado de los documentos dentro de la colección aplicando el filtro
        mCli['formio']['submissions'].update_one(
            {"data.nombreCmts": "CMT1.LUC1-LUC"},
            {
                "$set":{
                     "data": {
                        "nombreCmts": "CMT1.LUC2-LUC",
                        "vendorCmts": "LUC"
                            }
                        }
            }
        )
        result = "Dato modificado"
    except:
        result = "error al updatear dato"
    print(result)

def get_role_formio(host = "tambo_mongodb", port= 27017):
    # host = "tambo_mongodb"
    # port = 27017
    mCli = pymongo.MongoClient(host,port)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: forms
    mColForm = mDb["roles"]

    print (mColForm)
    data = []
   
    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        for doc in mColForm.find():
              data.append(doc)  
        result = data      
    except:
        result = "Error find"
    
    return(result)


t0 = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

t1 = PythonOperator(
    task_id='get_role_formio',
    python_callable=get_role_formio,
    tags=['REF'],
    dag=dag
    )

# t2 = PythonOperator(
#     task_id='Inserto_mongo',
#     python_callable=insert_mongo,
#     dag=dag
#     )

# t3 = PythonOperator(
#     task_id='Modifico_mongo',
#     python_callable=update_mongo,
#     dag=dag
#     )

# t4 = PythonOperator(
#     task_id='Leo_mongo_2',
#     python_callable=read_mongo,
#     dag=dag
#     )

# t0>>t1>>t2>>t3>>t4
t0>>t1
