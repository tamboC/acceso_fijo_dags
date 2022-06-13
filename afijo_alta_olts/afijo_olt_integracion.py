#con esta lineas agrego al path la carpeta del dag para poder leer libs propias
import sys
sys.path.insert(0,'/usr/local/airflow/dags/cel_afijo/afijo_alta_olts')
# sys.path.insert(1,'/usr/local/airflow/dags/lib')
#############################################################################
import os
import pprint

from airflow import DAG
from datetime import datetime, timedelta
from bson.objectid import ObjectId

from lib.tambo import *
from lib.L_afijo import *

from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python import BranchPythonOperator
# from netmiko_option.tamboOltHwOperator import TamboOltHwOperator
from teco_ansible.operators.TamboOltHwOperator import TamboOltHwOperator
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator
from template_config.hw.integracionOltHw import *

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
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

##################### Definicion de metodos################################
def check_ne_inventory(**context):
        data =context["dag_run"].conf.get("data")
        print(data)
        dataForm = TAMBO.GetForms(DAG_ID)
        olt_to_config = dataForm.get('nameOlt')
        print(f'olt_to_config:{olt_to_config}')
        #Datos para la funcion read_mongo_generic_find_one() --> Collection afijo_alta_olts
        db = 'tambo'
        collection='afijo_alta_olts'
        filter = {'nameOlt':olt_to_config}
        
        #Datos para la funcion read_mongo_generic_find_one() --> Collection hostname
        collection_hostname='hostname'
        filter_hostname = {'ShelfName': olt_to_config}
        
        #Leo la OLT desde la collection
        try:
            print('debug result find one')
            result_find_one = read_mongo_generic_find_one(db,collection,filter)
            print(result_find_one)
        except Exception as e:
            print(e)
        #Verifico que que la olt este en el inventario de Tambo para que funcione el filtro 
        result_find_one_hostname = read_mongo_generic_find_one(db,collection_hostname,filter_hostname)
        # print(result_find_one_hostname)
        dataOlt = {}
        if (result_find_one_hostname is None):
            print('Se procedera a insertar la OLT en el inventario de Tambo...')
            olt_to_insert_inventory_tambo = {
                "IPName":result_find_one['ipGestionOlt'],
                "IPSubnetMask":int(result_find_one['maskGestionCidr'].replace('/',"")),
                "BuildingName":None,
                "ShelfName":result_find_one['nameOlt'],
                "ShelfNetworkRole":"OLT_TMP",
                "ShelfState":"Pre-Active",
                "RackName":None,
                "RoomName":None,
                "BuildingLongitude":None,
                "BuildingLatitud":None,
                "BuildingAddress":None,
                "RegionName":None,
                "Subregion":None,
                "NetworkElement":result_find_one['nameOlt'],
                "Vendor":result_find_one['marcaOlt'],
                "Modelo":result_find_one['versionOlt'],
                "legacy":None,
                "LAB":"False",
                "PrePro":"True",
                "Prod":"True",
                "VersionFW":None,
                "VersionSW":None,
                "AccessTech":None,
                "Credenciales":None,
                "OperationalState del Shelf":None,
                "VARIABLES_CUSTOM":None,
                "ansible_network_os":None}
            result_insert = insert_mongo_generic_insert_one(db,collection_hostname,olt_to_insert_inventory_tambo)
            dataOlt = {"nameOlt" : result_find_one['nameOlt'],
                       "marcaOlt": result_find_one['marcaOlt']
            }
            
            # if isinstance(result_insert,dict):
            #     dataOlt = result_insert
        else:
            print('La OLT ya existe en el inv de Tambo')
            print(result_find_one_hostname)  
            #Armo el dict con la data a enviar a Ansible
            dataOlt = {"nameOlt" : result_find_one['nameOlt'],
                       "marcaOlt": result_find_one['marcaOlt']
            }

        context["dag_run"].conf = dataOlt
        return dataOlt

def get_vendor_olt(**context):
    data =context["dag_run"].conf.get("marcaOlt")
    print(data)
    if data == "Nokia":
        return "config_nk"
    elif data == "Huawei":
        return "get_data_by_olt_hw"

################# RAMA HW #################################################
def config_nk(**context):
    name_olt_config =context["dag_run"].conf.get("nameOlt")
    print(f"Se realizara la configuración de la OLT NK: {name_olt_config}")
    db = 'tambo'
    collection='afijo_alta_olts'
    filter = {'nameOlt': name_olt_config}
    result_find_one = read_mongo_generic_find_one(db,collection,filter)
    extra_vars_dict = {
        "nameOlt":result_find_one.get('nameOlt'),
        "nLinea":result_find_one.get('nLinea'),
        "ipGestionOlt":result_find_one.get('ipGestionOlt'),
        "ipGestionBng":result_find_one.get('ipGestionBng'),
        "maskGestionCidr":result_find_one.get('maskGestionCidr'),
        "maskGestionBin":result_find_one.get('maskGestionBin'),
        "ipToip":result_find_one.get('ipToip'),
        "ipToipOlt" : result_find_one.get('ipToipOlt'),
        "ipToipBng" : result_find_one.get('ipToipBng'),
        "maskToipCidr":result_find_one.get('maskToipCidr'),
        "maskToipBin":result_find_one.get('maskToipBin'),
        "marcaOlt":result_find_one.get('marcaOlt'),
        "modeloOlt":result_find_one.get('modeloOlt'),
        "versionOlt":result_find_one.get('versionOlt'),
        "puerto1Olt":result_find_one.get('puerto1Olt'),
        "puerto2Olt":result_find_one.get('puerto2Olt'),
        "statusDeployed":result_find_one.get('statusDeployed'),
        "topologiaDeConexion":result_find_one.get('topologiaDeConexion'),
        "emailTT":result_find_one.get('emailTT')}

    filter_for_playbook = {'ShelfName': name_olt_config}
    
    _operador_ansible = TamboAnsibleOperator(
                task_id='TamboAnsibleOperator_OLT_NK', 
                pbook_dir='/usr/local/airflow/dags/cel_afijo/afijo_alta_olts/ansible',
                playbook='deploy_config_nk.yml',
                connection='credenciales_olt_nk',
                mock=False,
                FILTRO_CUSTOM=filter_for_playbook,
                verbosity = 0,
                dict_extravars=extra_vars_dict) 

    _operador_ansible.execute()
    
    context["dag_run"].conf = extra_vars_dict
    
################# RAMA HW #################################################    
def get_data_by_olt_hw(**context):
    name_olt_config = []

    name_olt_config.append(context["dag_run"].conf.get("nameOlt"))
    comandos = {
                "consulta_1" : ["enable",
                                "display trap filter"],
                "consulta_2" : ["enable",
                                "undo smart",
                                "display board 0"]
            }  


    call_operator = TamboOltHwOperator(
                        task_id = "get_data_by_olt_hw_netmiko",
                        divice_name = name_olt_config, 
                        user = "root" , 
                        password = "Anacrusa7900#", 
                        commands = comandos, 
                        verbosity = 0)
    
    resultado = call_operator.execute(context)
    # resultado = {}


    resultado["nameOlt"] = context["dag_run"].conf.get("nameOlt")

    context["dag_run"].conf = resultado
    # print("Contex->")
    # print(context["dag_run"].conf)
    
def set_template_by_olt_hw(**context):
    
    # print("Contex->")
    # print(context["dag_run"].conf)

    name_olt_config = context["dag_run"].conf.get("nameOlt")

    # print("name_olt_config->")
    # print(name_olt_config)

    data_to_config = read_mongo_generic_find_one(g_db="tambo",g_collection="afijo_alta_olts", g_filter={"nameOlt": name_olt_config})
    
    # print("data_to_config->")
    # print(data_to_config)

    #Con la info obtenida del equipo parseo las alarmas actictivas del equipo para armar los comandos de config necesarios
    path_fsm_alarm = PATH_TEMPLATE + "hw/fsm/alarmas.fsm"
    data =context["dag_run"].conf.get("consulta_1").get("display trap filter") 
    data_parser_alarmas = parser_command(path_fsm=path_fsm_alarm , text_to_parse=data)
    print(data_parser_alarmas)

    #Con la info obtenida del equipo parseo las placas del equipo para armar los comandos de config necesarios
    path_fsm_board = PATH_TEMPLATE + "hw/fsm/placas.fsm"
    data =context["dag_run"].conf.get("consulta_2").get("display board 0") 
    data_parser_board = parser_command(path_fsm=path_fsm_board , text_to_parse=data)
    print(data_parser_board)

    my_dict = {}
    my_dict["set_commands_by_config"] = create_template_olt_hw(puerto1Olt=data_to_config.get("puerto1Olt"),puerto2Olt=data_to_config.get("puerto2Olt"),ipToipOlt=data_to_config.get("ipToipOlt"),maskToipBin=data_to_config.get("maskToipBin"),collection_of_alarms=data_parser_alarmas,collection_of_boards=data_parser_board)
    my_dict["nameOlt"] = context["dag_run"].conf.get("nameOlt")


    context["dag_run"].conf = my_dict
    # print(context["dag_run"].conf)

def config_hw(**context):

    name_olt_config = []
    set_commands_by_config = {}
    # print(context["dag_run"].conf)

    name_olt_config.append(context["dag_run"].conf.get("nameOlt"))
    
    data_olt = read_mongo_generic_find_one(g_db="tambo",g_collection="afijo_alta_olts", g_filter={"nameOlt": name_olt_config[0]})
    print(name_olt_config)
    print(data_olt)


    set_commands_by_config =context["dag_run"].conf.get("set_commands_by_config")
    print(set_commands_by_config)

    call_operator = TamboOltHwOperator(
                        task_id = "config_olt_hw_netmiko",
                        divice_name = name_olt_config, 
                        user = "root" , 
                        password = "Anacrusa7900#", 
                        commands = set_commands_by_config, 
                        verbosity = 0)
    
    resultado = call_operator.execute(context)

    data_olt.pop('_id', None)
    context["dag_run"].conf = data_olt

################# check Config ############################################

def check_config(**context):
    data = context["dag_run"].conf
    pp = pprint.PrettyPrinter(indent=4)
    context["dag_run"].conf = data

def send_mail(**context):
    mi_mail = context["dag_run"].conf.get("emailTT")
    mi_subject = "[TAMBO] - ALTA OLT: {} - WF1 - Configuracion de Integracion".format(context["dag_run"].conf.get("nameOlt"))
    mi_content = """
    <strong>Configuración de Integración de la OLT {0}</strong>
    <br><br>
    Se realizo la configuración de integración de la OLT {0} modelo {1} - {2}.
    <br><br><br>
    Este es un mail enviado automaticamente desde la plataforma TAMBO.
    <br><br>
    <strong>BY IMPLEMENTACIONES DE ACCESOS FIJO</strong>
    <br>
    no responda a este mail, por consultas a implementacioneslogicas@teco.com.ar
    """.format(context["dag_run"].conf.get("nameOlt"), context["dag_run"].conf.get("marcaOlt"),  context["dag_run"].conf.get("modeloOlt"))
    
    email_op = EmailOperator(
                task_id='send_email',
                to = mi_mail,
                subject = mi_subject,
                html_content = mi_content,
                files=None
            )
    email_op.execute(context)

def update_status_db(**context):

    db = 'formio'
    collection='submissions'
    filter = {"data.nameOlt" : context["dag_run"].conf.get('nameOlt')}
    data = {"data": {
                        "nameOlt": context["dag_run"].conf.get('nameOlt'),
                        "status": "DEPLOYED"
                    }
            }

    result_change_one = update_mongo_generic_update_one(db,collection,filter,data)
    print(result_change_one)

    db_1 = 'tambo'
    collection_1='afijo_alta_olts'
    filter_1 = {"nameOlt" : context["dag_run"].conf.get('nameOlt')}
    data_1 = {"statusDeployed": "DEPLOYED"}

    result_change_one_1 = update_mongo_generic_update_one(db_1,collection_1,filter_1,data_1)
    print(result_change_one_1)

################ intancia de los operadores ##############################

_get_vendor_olt = BranchPythonOperator(
                                        task_id='get_vendor_olt',
                                        python_callable=get_vendor_olt,
                                        dag=dag
                                        )

_check_ne_inventory = PythonOperator(
                                        task_id='check_ne_inventory',
                                        python_callable=check_ne_inventory,
                                        provide_context=True,
                                        dag=dag
                                        )

_config_nk = PythonOperator(
                            task_id='config_nk',
                            python_callable=config_nk,
                            provide_context=True,
                            dag=dag
                            )

_get_data_by_olt_hw = PythonOperator(
                            task_id='get_data_by_olt_hw',
                            python_callable=get_data_by_olt_hw,
                            provide_context=True,
                            dag=dag
                            )

_set_template_by_olt_hw = PythonOperator(
                            task_id='set_template_by_olt_hw',
                            python_callable=set_template_by_olt_hw,
                            provide_context=True,
                            dag=dag
                            )

_config_hw = PythonOperator(
                            task_id='config_hw',
                            python_callable=config_hw,
                            provide_context=True,
                            dag=dag
                            )

_check_config  = PythonOperator(
                            task_id='check_config',
                            python_callable=check_config,
                            provide_context=True,
                            trigger_rule="one_success",
                            dag=dag
                            )

_send_mail = PythonOperator(
                            task_id='send_mail',
                            python_callable=send_mail,
                            provide_context=True,
                            dag=dag
                            )

_update_status_db = PythonOperator(
                            task_id='update_status_db',
                            python_callable=update_status_db,
                            provide_context=True,
                            dag=dag
                            )

################# llamada a los operadores#########################3
_check_ne_inventory >> _get_vendor_olt >> _config_nk >> _check_config 
_check_ne_inventory >> _get_vendor_olt >> _get_data_by_olt_hw >> _set_template_by_olt_hw >> _config_hw >> _check_config


_check_config >>_send_mail 
_check_config >>_update_status_db 