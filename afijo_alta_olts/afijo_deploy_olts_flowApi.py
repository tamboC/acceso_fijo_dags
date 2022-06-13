
import json
from datetime import datetime
from teco_ansible.operators.TamboAnsibleOperator import TamboAnsibleOperator
from lib.tambo import *
from lib.L_afijo import *
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

@dag(schedule_interval=None, start_date=datetime(2022, 2, 4), catchup=False, tags=['FTTH','OLT'])
def afijo_deploy_olts_flowApi():
    @task()
    def verified_hostname():
        context = get_current_context()
        data =context["dag_run"].conf.get("data")
        print(data)
        dataForm = TAMBO.GetForms('afijo_deploy_olts_flowApi')
        olt_to_config = dataForm.get('OLTaConfigurar')
        print(f'olt_to_config:{olt_to_config}')
        host_test_hostname = 'BUAP01'
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
            
            if isinstance(result_insert,dict):
                dataOlt = result_insert
        else:
            print('La OLT ya existe en el inv de Tambo')
            print(result_find_one_hostname)  
            #Armo el dict con la data a enviar a Ansible
            dataOlt = {"nameOlt" : result_find_one['nameOlt'],
                       "marcaOlt": result_find_one['marcaOlt']
            }

        return dataOlt

    @task()
    def execute_playbook(data):
        print(data)
        print(f'Datos de la task previa: {data}')
        #Datos para la funcion read_mongo_generic_find_one() --> Collection afijo_alta_olts
        db = 'tambo'
        collection='afijo_alta_olts'
        filter = {'nameOlt':data.get('nameOlt')}
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
            "emailTT":["implementaciones_logicas@teco.com.ar"]}

        # comandos = {'mykey': ['display version','display clock']}
        data_for_playbook = {'ShelfName': data.get('nameOlt')}
        print(data)
        
        ##Se busca el Vendor de la olt a configurar
        vendor = data.get('marcaOlt')
        if vendor == 'Huawei':
            print("Entre en Nk")
            _test_operador_ansible = TamboAnsibleOperator(
                task_id='TestOperadorAnsible', 
                pbook_dir='/usr/local/airflow/dags/cel_afijo/afijo_alta_olts/ansible',
                playbook='deploy_config_hw.yml',
                # playbook='afijo_extra_vars.yml',
                connection='credenciales_olt_hw_r20',
                mock=False,
                FILTRO_CUSTOM=data_for_playbook,
                dict_extravars=extra_vars_dict)            
            _test_operador_ansible.execute()

        if vendor == 'Nokia':
            print("Entre en Nk")
            _test_operador_ansible = TamboAnsibleOperator(
                task_id='TestOperadorAnsible', 
                pbook_dir='/usr/local/airflow/dags/cel_afijo/afijo_alta_olts/ansible',
                playbook='deploy_config_nk.yml',
                # playbook='afijo_extra_vars.yml',
                connection='credenciales_olt_nk',
                mock=False,
                FILTRO_CUSTOM=data_for_playbook,
                verbosity = 5,
                dict_extravars=extra_vars_dict)            
            _test_operador_ansible.execute()
        else:
            print('No se Ejecuto ninngun playbook')

    data = verified_hostname()
    execute_config = execute_playbook(data)

#Execute DAG
etl_dag = afijo_deploy_olts_flowApi()
