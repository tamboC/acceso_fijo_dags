from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from lib.tambo import *
import os
import sys
import pymongo
import json
from datetime import datetime, timedelta
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator
from teco_db.operators.tecoMongoDbOperator import TecoReadMongo
from bson.objectid import ObjectId
from airflow.models import XCom
import base64
import yaml 
import csv
import jinja2
#from sendmail import *  

from lib.L_afijo import *

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")

def test(context):
    print('success callback')
    
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
    tags=['CCAP'],
    default_args=default_args
)


#Python Callables
###################

def readFormio (**kwargs):

    debuging = True

    formulario = TAMBO.GetForms(DAG_ID)
    
    logging.info (formulario)


    #####SETEO DE VARIABLES######
    cmtsNombre = formulario['nombreGeneradoDelCmts']
    cmtsNro = formulario['cmtSx']
    hub = formulario['hub']
    vendor = formulario['vendor']

    lista_placas=[]
    if formulario["lineCard1"]:
        lista_placas.append('1')
    if formulario["lineCard2"]:
        lista_placas.append('2')
    if formulario["lineCard3"]:
        lista_placas.append('3')
    if formulario["lineCard6"]:
        lista_placas.append('6')
    if formulario["lineCard7"]:
        lista_placas.append('7')
    if formulario["lineCard8"]:
        lista_placas.append('8')
    if formulario["lineCard9"]:
        lista_placas.append('9')
    
    cantidadDePlacas = ','.join(lista_placas)
    portchannel = formulario['portchannel']

    #####Requiere DSG######
    haveDsg =formulario['hubConDsg']
    grupoDsg=''    ########## VER TEMA DSG 16/03 con javi #########
    if formulario['hubConDsg']:
        #direccionDeRadd = formulario['direccionDeRadd']
        #numeroDeTunnelDeApp = formulario['panelFieldsetTableAppId']
        grupoDsg_dict = formulario['panelSelect']
        print(grupoDsg_dict)
        grupoDsg = grupoDsg_dict['data']['grupo']
        print(grupoDsg)
    else:
        direccionDeRadd = ""
        numeroDeTunnelDeApp = ""

    cmtsLoopDirIPv4 = formulario['loopbackIPv4']

     #####Requiere loopbakc de IPv6######
    haveLoopback=formulario['loopbackIpv6']
    if formulario['loopbackIpv6']:
        cmtsLoopDirIPv6 = formulario['loopbackIpv6']
    else:
        cmtsLoopDirIPv6 = ""
        
    roaLoopdir = formulario['direccionDeLoopbackDelBngRoa']
    cmtsDatosIPv4 = formulario['datosVlanIpv4']
    
    #####Requiere vlan de IPv6######
    haveIpv6=formulario['loopbackIpv6']
    if formulario['dirDatosVlanIpv6']:
        cmtsDatosIPv6 = formulario['dirDatosVlanIpv6']
    else:
        cmtsDatosIPv6 = ""
        
    cmtsToipIPv4 = formulario['toIpVlanIpv4']
    cmtsControlIPv4 = formulario['controlVlanIpv4']
    vlanNro = formulario['cmtSx'][3]

    #####Generacion del JSON para la plantilla Jinja######
    CMTS = {}
    CMTS["cmtsNombre"]=cmtsNombre
    CMTS["cantidadDePlacas"]=cantidadDePlacas
    CMTS["portchannel"]=portchannel
    #CMTS["direccionDeRadd"]=direccionDeRadd
    #CMTS["numeroDeTunnelDeApp"]=numeroDeTunnelDeApp
    CMTS["cmtsLoopDirIPv4"]=cmtsLoopDirIPv4
    CMTS["cmtsLoopDirIPv6"]=cmtsLoopDirIPv6
    CMTS["roaLoopdir"]=roaLoopdir
    CMTS["cmtsDatosIPv4"]=cmtsDatosIPv4
    CMTS["cmtsDatosIPv6"]=cmtsDatosIPv6
    CMTS["cmtsToipIPv4"]=cmtsToipIPv4
    CMTS["cmtsControlIPv4"]=cmtsControlIPv4
    CMTS["vlanNro"]=vlanNro
    CMTS["dirDatosVlanIpv6"]=formulario['dirDatosVlanIpv6']
    CMTS["hubConDsg"]=formulario['hubConDsg']
    CMTS["loopbackIpv6"]=formulario['loopbackIpv6']
    CMTS["emails"]=formulario['emails']
    
    logging.info(json.dumps(CMTS,indent=2))

    kwargs["dag_run"].conf.update({"new_ccap" : CMTS})            


def saveCCAPinfo  (**kwargs):

    new_ccap = kwargs["dag_run"].conf.get("new_ccap")       # recupero informacion del CCAP 
    logging.info(json.dumps(new_ccap,indent=2))  

    #Datos para la funcion read_mongo_generic_find_one() --> Collection afijo_alta_olts
    db = 'tambo'
    collection='afijo_alta_cmts'
    filter = {'cmtsNombre':new_ccap}
        
       
    #Leo el CCAP desde la collection
    try:
        print('debug result find one')
        result_find_one = read_mongo_generic_find_one(db,collection,filter)
        print(result_find_one)
    except Exception as e:
        print(e)


    if (result_find_one is None):
        print('Se procedera a insertar el CCAP en el inventario de Tambo...')
        result = insert_mongo_generic_insert_one(g_db="tambo",g_collection=collection,g_data=new_ccap)
        mail_type = 0
    else:
        logging.info ("El CCAP fue cargado previamente!!!")
        MAIL_TYPE = 1
        subject = '[MAT] - ALTA CMTS: {0} - Configuracion inicial de la Gestion NO OK'.format(cmtsNombre)
        msg_body = """No fue posible emitir la configuracion inicial de {0} ya que el mismo se encuentra en el Content de MAT. Se recomienda revisar la tabla en MAT para determinar si es correcta o se debe eliminar el registro.
        
        Este es un mail enviado automaticamente desde la plataforma MAT.""".format(cmtsNombre)
        mail_type = 1

    logging.info(result)
    
    kwargs["dag_run"].conf.update({"mail_type" : mail_type})            



def generateConfig  (**kwargs):

    new_ccap = kwargs["dag_run"].conf.get("new_ccap")       # recupero informacion del CCAP 
    mail_type = kwargs["dag_run"].conf.get("mail_type")       # recupero informacion del CCAP 

    #print (json.dumps(new_ccap,indent=2))  

    #####Envio de mails######
    emails = new_ccap['emails']
 #   separador = ";"
 #    lista_mails = separador.join(emails)
    lista_mails  = emails
    logging.info (lista_mails)
#    render_plantilla(CMTS, path_root, path_working_folder)
    path_template = '/usr/local/airflow/dags/cel_afijo/afijo_prueba_alta_cmts/templates'
    templateLoader = jinja2.FileSystemLoader(searchpath=path_template)
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("template_config_day0_CBR8.j2")
    output_from_parsed_template = template.render(new_ccap)
    print (output_from_parsed_template)

    folder_config = '/io/cel_afijo/tmp/alta_cmts/CBR8/{0}'.format(new_ccap["cmtsNombre"])

    try:
        os.stat(folder_config)
    except:
        os.mkdir(folder_config)

    uri ='/io/cel_afijo/tmp/alta_cmts/CBR8/{0}/config_day0.cfg'.format(new_ccap["cmtsNombre"])
    with open (uri, "w") as config_day0_file:
        config_day0_file.write(output_from_parsed_template)

#    if mail_type==0:
#        render_plantilla(CMTS, path_root, path_working_folder)
#        subject = '[TAMBO] - ALTA CMTS: {0} - Configuracion inicial de la Gestion OK'.format(new_ccap["cmtsNombre"])
#        msg_body = """Se adjunta en archivo de texto la configuracion inicial del equipo {0} para levantar su gestion.
#        Para termina de habilitar gestion por ssh ejecutar los siguiente comando de configuracion:
        
#        configure terminal
#         ip domain name www.cablevision.com.ar
#         crypto key generate rsa 
#         !!! ingresar el valor 768 + enter
#         no ip domain name www.cablevision.com.ar
#        exit 
#        
#        Este es un mail enviado automaticamente desde la plataforma MAT.""".format(new_ccaps["cmtsNombre"])
#
#         send_mail(mi_mail, mi_subject, mi_content, path_file)

#    else:
#        SendEmailTLS(
#            dest=lista_mails, 
#            subj=subject, 
#            msg=msg_body)

###############DEF TASK

read_formio = PythonOperator(
    task_id='Read_Formio',
    python_callable=readFormio,
    provide_context=True,
    dag=dag 
    ) 

save_CCAP_info = PythonOperator(
    task_id='Save_CCAP_Info',
    python_callable=saveCCAPinfo,
    provide_context=True,
    dag=dag 
    ) 

generate_config = PythonOperator(
    task_id='Generate_Config',
    python_callable=generateConfig,
    provide_context=True,
    dag=dag 
    ) 



###############CALL TASK

read_formio >> save_CCAP_info >> generate_config