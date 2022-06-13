import os
import pymongo
import jinja2

from airflow import DAG
from datetime import datetime, timedelta
from bson.objectid import ObjectId

from lib.tambo import *
from lib.L_afijo import *

from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")

##Cosntantes GLOBALES####
PRE_DEPLOYED = "PRE_DEPLOYED"
DEPLOYED = "DEPLOYED"
PATH_TEMPLATE = "/usr/local/airflow/dags/cel_afijo/afijo_alta_olts/template_config/"

#arg
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 1, 1),
    'email': ['tambo_afijo@teco.com.ar'],
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
    tags=['ALTA', 'FTTH'],
    default_args=default_args
)

###############Metodos######################



def insert_mongo(**kwargs):
    dataForm = TAMBO.GetForms(DAG_ID)
    print (dataForm)

    nameOlt = dataForm.get("nombreOlt")
    nLinea = dataForm.get("nLinea")
    ipGestionOlt = custom_ip(dataForm.get("ipGestion"),2)
    ipGestionBng = custom_ip(dataForm.get("ipGestion"),1)
    maskGestionCidr = "/30"
    maskGestionBin = "255.255.255.252"
    ipToip = dataForm.get("iptoip")
    ipToipOlt = custom_ip(dataForm.get("iptoip"),2)
    ipToipBng = custom_ip(dataForm.get("iptoip"),1)
    maskToipCidr = mask_cidr(dataForm.get("masktoip"))
    maskToipBin = dataForm.get("masktoip")
    topologiaDeConexion = dataForm.get("topologiaDeConexion")
    emailTT = dataForm.get("emailTT")

    modeloOlt = dataForm.get("modeloOlt")
    marcaOlt = trans_modelo_olt(dataForm.get("modeloOlt") , "marcaOlt")
    modeloOlt = trans_modelo_olt(dataForm.get("modeloOlt") , "modeloOlt")
    versionOlt = trans_modelo_olt(dataForm.get("modeloOlt") , "versionOlt")
    puerto1Olt = trans_modelo_olt(dataForm.get("modeloOlt") , "puerto1Olt")
    puerto2Olt = trans_modelo_olt(dataForm.get("modeloOlt") , "puerto2Olt")
    

    dataOlt = { "nameOlt" : nameOlt,
                "nLinea" : nLinea,
                "ipGestionOlt" : ipGestionOlt,
                "ipGestionBng" : ipGestionBng,
                "maskGestionCidr" : maskGestionCidr,
                "maskGestionBin": maskGestionBin , 
                "ipToip" : ipToip,
                "ipToipOlt" : ipToipOlt,
                "ipToipBng" : ipToipBng,
                "maskToipCidr" : maskToipCidr,
                "maskToipBin" : maskToipBin,
                "marcaOlt" : marcaOlt,
                "modeloOlt" : modeloOlt,
                "versionOlt" : versionOlt,
                "puerto1Olt" : puerto1Olt,
                "puerto2Olt" : puerto2Olt,
                "statusDeployed" : PRE_DEPLOYED,
                "topologiaDeConexion" : topologiaDeConexion,
                "emailTT" : emailTT
            }

    result = insert_mongo_generic_insert_one(g_db="tambo",g_collection="afijo_alta_olts",g_data=dataOlt)
    
    print(result)

    datetime_now = datetime.now()
    data_resourse = { 
        "owner": ObjectId("61670cb259535635ead8ab4a"),
        "deleted":None,
        "roles":[],
        "data":
            {"nameOlt": nameOlt,
            "status": "PRE_DEPLOY"},
        "access":[],
        "form":ObjectId("61672240595356d470d8ac27"),
        "externalIds":[],
        "created":datetime_now,
        "modified":datetime_now,
        "__v":0}

    result = insert_mongo_generic_insert_one(g_db="formio",g_collection="submissions",g_data=data_resourse)

    
def send_mail_custom(**context):
    dataForm = TAMBO.GetForms(DAG_ID)

    dataolt = read_mongo(name_olt = dataForm.get("nombreOlt") ,db= "tambo" ,collection = "afijo_alta_olts", host = "tambo_mongodb", port = 27017)
    
    mi_mail = dataolt[0].get("emailTT")

    mi_subject = "[TAMBO] - ALTA OLT: {} - WF0 - Configuracion de Gestion".format(dataolt[0].get("nameOlt"))
    
    mi_content = """
        <strong>Configuración de Gestión de la OLT {0}</strong>
        <br><br>
        En los archivos adjuntos se pueden observar las configuraciones para la gestion de la OLT {0} modelo {1} - {2}.
        <br><br><br>
        Este es un mail enviado automaticamente desde la plataforma TAMBO.
        <br><br>
        <strong>BY IMPLEMENTACIONES DE ACCESOS FIJO</strong>
        <br>
        no responda a este mail, por consultas a implementacioneslogicas@teco.com.ar
        """.format(dataolt[0].get("nameOlt"), dataolt[0].get("marcaOlt"), dataolt[0].get("modeloOlt"))



    if dataolt[0].get("marcaOlt") == 'Huawei':
        template = "gestionOltHw.j2"
        path_template = PATH_TEMPLATE + "hw"
    elif dataolt[0].get("marcaOlt") == 'Nokia':
        template ="gestionOltNk.j2"
        path_template = PATH_TEMPLATE + "nk"

    file = render_plantilla(data_dict = dataolt[0], path_template = path_template, name_template = template)

    print(file)

    path_file = "/io/cel_afijo/tmp/alta_olt/config_init/Config_init_OLT_"+ dataForm.get("nombreOlt") + ".txt"

    fh = open(path_file,"w")
    fh.write(file)
    fh.close()

    
 

    send_mail(mi_mail, mi_subject, mi_content, path_file)
    
#############################################################################################################################
#Operadores
#############################################################################################################################
ini = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

#############################################################################################################################
# insertamos los datos en la mongo 
#############################################################################################################################
_insert_data_db = PythonOperator(
    task_id='Insert_Data_DB',
    python_callable=insert_mongo,
    provide_context=True,
    dag=dag
    )

#############################################################################################################################
# Operador python que internamente ejecuta el operador EmailOperator pero permite editar las variables del mismo
#############################################################################################################################

_send_mail_custom = PythonOperator(
   task_id='send_email_custom',
   python_callable=send_mail_custom,
   provide_context=True,
   dag=dag
)    
#############################################################################################################################
# Dag RUN
#############################################################################################################################
ini >> _insert_data_db >> _send_mail_custom