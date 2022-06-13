import os
import sys
import pymongo
import pprint
import json
from bson.objectid import ObjectId
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
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
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}
        
###################### def del dag ##########################
dag = DAG(
    dag_id= DAG_ID, 
    schedule_interval= None, 
    tags=['FORMIO'],
    default_args=default_args
)

############################################################
def get_env() -> dict:
    """Metodo que devuelve un diccionarion con el nombre del entorno y su ip donde esta corriendo el DAG.
        el nombre sale de la variable de entorno $FA_ENTORNO 
        (se puede verificar entrando al docker de airflow y hacer un 'echo $FA_ENTORNO')
        
        Salidas posibles:  
         
         data = {"name_env" : "fa-dev", 
                 "ip_env": "10.247.2.44"}
         
         data = {"name_env" : "fa-test", 
                 "ip_env": "10.247.2.43"}
         
         data = {"name_env" : "fa-prod", 
                 "ip_env": "10.247.2.42"}
    """
    # Get the list of user's environment variables
    env_var = dict(os.environ).get("FA_ENTORNO")
    # Print the list of user's environment variables
    # print(f'Environment variable: {env_var}')
    
    data = {
        "name_env" : env_var,
        "ip_env": ""
    }

    if env_var == "fa-dev":
        data["ip_env"] = "10.247.2.44"  
    elif env_var == "fa-test":
        data["ip_env"] = "10.247.2.43"  
    elif env_var == "fa-prod":
        data["ip_env"] = "10.247.2.42" 
    else:
        data["ip_env"] = None
        
    return data 

def set_ip_env(in_env = None):
    env = get_env()
    
    if in_env == env.get("name_env"):
        host = "tambo_mongodb"
    elif in_env == "prod":
        host = "10.247.2.42"
    elif in_env == "test":
        host = "10.247.2.43"
    elif in_env == "fa-dev":
        host = "10.247.2.44"
    else:
        host = None
    
    return host

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

def check_form(title_form = None, db = None, collection= None, host = None, port= 27017):
    mCli = pymongo.MongoClient(host,port)
    mDb = mCli[db]
    mCollection = mDb[collection]
    form = []
    try:
        for doc in mCollection.find({"title": title_form}):
            form.append(doc)
        cant_form = len(form)
        print(f'La cantidad de formularios encontrados en la db {db}.{collection}  del entorno {host} es: {cant_form}')
        if cant_form >= 1:
            return True
        else:
            return False
    except:
        print(f'Error al buscar los formularios')
        return False

def new_form(title_form = None, data = {}, db = None, collection= None, host = None, port= 27017):
    mCli = pymongo.MongoClient(host,port)
    #SETEO la DB a USAR : formio
    mDb = mCli[db]
    #SETEO la colección: forms
    mColForm = mDb[collection]
    datetime_now = datetime.now()
    form_temp = {
        "type": data.get("type"),
        "tags": data.get("tags"),
        "deleted": data.get("deleted"),
        "owner": data.get("owner"),
        "components": data.get("components"),
        "display": data.get("display"),
        "submissionAccess": data.get("submissionAccess"), 
        "title": data.get("title"),
        "name": data.get("name"),
        "path": data.get("path"),
        "access": data.get("access"),
        "created": datetime_now,
        "modified": datetime_now,
        "machineName": data.get("machineName"),
        "__v": data.get("__v")
    }
    print (form_temp)

    result = {"result" : None,
                "_id": None}
  
    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        insert_data = mColForm.insert_one(form_temp)
        result["result"] = "Dato insertado"
        result["_id"] = insert_data.inserted_id
    
    except:
        result["result"] = "Error al insertar dato"
    # print(result)
    return(result)

def set_actions(data = {}, id_form = None, db = None, collection= None, host = None, port= 27017):
    mCli = pymongo.MongoClient(host,port)
    #SETEO la DB a USAR : formio
    mDb = mCli[db]
    #SETEO la colección: forms
    mColForm = mDb[collection]
    result = {}
    for index, action in enumerate(data):
        result[str(index)] = {}
        action_temp = {
                        "handler": action.get("handler"),
                        "method": action.get("method"),
                        "priority": action.get("priority"),
                        "deleted": action.get("deleted"),
                        "title": action.get("title"),
                        "name": action.get("name"),
                        "form": id_form,
                        "machineName": action.get("machineName"),
                        "__v": action.get("__v")
                        }
        pprint.pprint(action_temp)  
        try:
            #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
            insert_data = mColForm.insert_one(action_temp)
            result[str(index)]["result"] = "Action insertado"
            result[str(index)]["_id"] = insert_data.inserted_id

        except:
            result[str(index)]["result"] = "Error al insertar Actions"
    return(result)

def update_form(title_form = None, data = {}, db = None, collection= None, host = None, port= 27017):
    mCli = pymongo.MongoClient(host,port)
    #SETEO la DB a USAR : formio
    mDb = mCli[db]
    #SETEO la colección: forms
    mColForm = mDb[collection]
    datetime_now = datetime.now()
    form_temp = {
            "$set" : {
                "tags": data.get("tags"),
                "components": data.get("components"),
                "display": data.get("display"),
                "submissionAccess": data.get("submissionAccess"), 
                "access": data.get("access"),
                "modified": datetime_now
                    }
                }
    print (form_temp)
    result = {"result" : None,
            "_id": data.get("_id")}
    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        data = mColForm.update_one({"title": data.get("title")},form_temp)
        result["result"] = "Dato Actualizados"
    except:
        result["result"] = "Error al actualizar los dato"
    return(result)

def get_role_formio(host = None, port= 27017):
    mCli = pymongo.MongoClient(host,port)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: roles
    mColForm = mDb["roles"]
    try:
        data = []   
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        for doc in mColForm.find():
              data.append(doc)  
        result = data      
    except:
        result = "Error find"
    return(result)

def get_id_user_destino(id_origen = None, roles_origen = None, roles_destino= None):
    temp_name_role = ""
    id_role_destino = ""

    for id_usuario in roles_origen:
        if id_origen == id_usuario.get('_id'):
            temp_name_role = id_usuario.get('title')

    for id_usuario in roles_destino:
        if temp_name_role == id_usuario.get('title'):
            id_role_destino = id_usuario.get('_id')

    print (f"El id en el origen es: {id_origen} del usuario {temp_name_role}. El id de destino es: {id_role_destino}")

    return id_role_destino

def get_actions_form(id_origen = None, host_origen = None, port= 27017):
    mCli = pymongo.MongoClient(host_origen,port)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: roles
    mColForm = mDb["actions"]

    try:
        data = []   
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        for doc in mColForm.find({"form": id_origen}):
              data.append(doc)  
        result = data      
    except:
        result = "Error find"
    return(result)

def main(**kwargs):
    id_submit=kwargs["dag_run"].conf.get("_id")
    print (f"El id del submit es: {id_submit}")
    #importo de la mongo los datos insertados en el formularios por el usuario, usando el _id de submission
    data_submit = read_mongo(id_submit=id_submit,name_form=None,db="formio",collection="submissions",host="tambo_mongodb")[0]

    entorno_origen = data_submit.get('data').get('origenEntorno')
    name_form_origen = data_submit.get('data').get('origenTituloForm')
    entorno_destino = data_submit.get('data').get('destinoEntorno')
    name_form_destino = data_submit.get('data').get('destinoTituloForm')

    print(f'El entorno de origen es: {entorno_origen}')
    print(f'El formulario de origen es: {name_form_origen}')
    print(f'El entorno de destino es: {entorno_destino}')
    print(f'El formulario de destino es: {name_form_destino}')
    
    #determino la ip del host origen
    host_origen = set_ip_env(in_env=entorno_origen)
    print(f'host origen {host_origen}')

    #determino la ip del host destino
    host_destino = set_ip_env(in_env=entorno_destino)
    print(f'host destino {host_destino}')
  
    #importo los datos del formulario a migrar
    data_form = read_mongo(id_submit=None,name_form = name_form_origen,db="formio",collection="forms",host=host_origen)[0]
    # pprint.pprint(data_form)

    #importo los roles creados en el formio de host origen y destino
    roles_origen = get_role_formio(host = host_origen)
    roles_destino = get_role_formio(host = host_destino)

    # pprint.pprint(roles_origen)
    # pprint.pprint(roles_destino)

    #recorro la key de access al formulario y le actualizo los roles con el ID destino
    for index, user in enumerate(data_form.get('access')[0].get('roles')):
        # print(index)
        # print(user)
        # print(data_form.get('access')[0].get('roles')[index[0]])
        data_form.get('access')[0].get('roles')[index] = get_id_user_destino(id_origen = ObjectId(user), roles_origen = roles_origen, roles_destino= roles_destino)
    
    # pprint.pprint(data_form.get('access')[0].get('roles'))
    
    for submission_access in data_form.get('submissionAccess'):
        # print (submission_access)
        
        for index, user in enumerate(submission_access.get('roles')):
            # print(index)
            # print(user)
            submission_access.get('roles')[index] = get_id_user_destino(id_origen = ObjectId(user), roles_origen = roles_origen, roles_destino= roles_destino)
    
    # pprint.pprint(data_form)

    #verifico si existe el formulario en el destino, si existe lo actualizo sino lo creo
    if check_form(name_form_destino, "formio", "forms", host = host_destino):
        print(f'El formulario {name_form_origen} existe dentro del entorno {entorno_destino}, se realizara la actualización del formilario existente.')
        status_insert = update_form(title_form= name_form_destino, data = data_form , db = "formio", collection = "forms", host = host_destino)
        print(status_insert)
    else:    
        print(f'El formulario {name_form_origen} NO existe dentro del entorno {entorno_destino}, se va a migrar el formulario.')
        status_insert_form = new_form(title_form= name_form_destino, data = data_form , db = "formio", collection = "forms", host = host_destino)
        pprint.pprint(status_insert_form)
        actions_origen = get_actions_form(id_origen = data_form.get('_id'), host_origen = host_origen)
        pprint.pprint(actions_origen)
        status_insert_actions = set_actions(data = actions_origen, id_form = status_insert_form.get("_id"), db = "formio", collection= "actions", host = host_destino)
        pprint.pprint(status_insert_actions)

#################################################################3
task_1 = PythonOperator(
    task_id='Migration_Form',
    python_callable=main,
    provide_context=True,
    dag=dag
    )

#################################################################

task_1
