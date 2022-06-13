"""
    Documentar codigo con Docstring

"""
import os
import sys
import json
import pymongo
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from teco_db.operators.tecoMongoDbOperator import TecoReadMongo
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
    default_args=default_args
)
    
#función para habilitar el código del DAG en Sphinx
def doc_sphinx():
    pass

#python callables:
def lectura(**context):
    query = TecoReadMongo(
    task_id='read',
    table='CMTS-PuertosFisicos',
    query = {'cmts':'CMT1.AVA1-CBR8'},
    provide_context=True,
    dag=dag)

    combinaciones = query.execute()
    #print("tipo: ", type(combinaciones))
    #print("contendido: ",combinaciones)

    #El operador TecoReadMongo solo permite leer desde la DB Tambo, debo leer de formio
    '''objeto = TecoReadMongo(
    task_id='read',
    table='submisssions',
    query = {'channelMapName':'1'},
    provide_context=True,
    dag=dag)'''

    #Utilizo directamente pymongo
    HOST = 'tambo_mongodb'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    mDb = mCli["formio"]
    mColForm = mDb["forms"]


    for combinacion in combinaciones:
        print("\ncoso: ", combinacion )
    
        try:
            print(int(combinacion['dw_channel_map']))
            dw_channel = str(int(combinacion['dw_channel_map']))
        except:
            print(combinacion['dw_channel_map'])
            dw_channel =  (combinacion['dw_channel_map'])
        finally:
            print(type(combinacion['dw_channel_map']))

        try:
            print(int(combinacion['up_channel_map']))
            up_channel = str(int(combinacion['up_channel_map']))
        except:
            print(combinacion['up_channel_map'])
            up_channel = (combinacion['up_channel_map'])
        finally:
            print(type(combinacion['up_channel_map']))
    
    
        if dw_channel == dw_channel: #Verifica que no sea NaN
            x = mColForm.find_one({'path':"dwchannelmaps"}) #obtengo id del formulario en mongo
        
            filter={
                'form': (x['_id']), #utilizo el id para traerme todo lo del formulario
                'deleted': None,
                'data.channelMapName': dw_channel
            }

            result = mCli['formio']['submissions'].find_one(
            filter=filter,
            )#.pretty()

            if result == None:
                raise Exception(f"DW Channel Map no definido en DB: {w_channel}")
            else:
                print(result)


        

        if up_channel == up_channel: #verifica que no sean Nan
            x = mColForm.find_one({'path':"upchannelmaps"}) #obtengo id del formulario en mongo
            
            filter={
                'form': (x['_id']), #utilizo el id para traerme todo lo del formulario
                'deleted': None,
                'data.channelMapName': up_channel
            }

            result = mCli['formio']['submissions'].find_one(
            filter=filter,
            )#.pretty()

            if result == None:
                raise Exception('UP Channel Map no definido en DB: %s' % up_channel)
            else:
                print(result)

        #resultado = objeto.execute()

        #json.dump(resultado,'/io/cel_afijo/tmp/salidaquery.json')


#tasks
t0 = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

t1 = PythonOperator(
    task_id='read_coso',
    python_callable=lectura,
    dag=dag
    )

t0>>t1