"""
    Documentar codigo con Docstring
    Path de este directorio /usr/local/airflow/dags/cel_afijo
    Path de la carpeta Ansible /urs/local/ansible/
"""
import os
import sys
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from teco_db.operators.tecoMongoDbOperator import TecoMongoDb
from lisy_plugin.operators.lisy_operator import *
from datetime import datetime, timedelta
import re
import json
import jinja2 
import os
from teco_ansible.operators.tecoAnsibleOperator import tecoCallAnsible
from teco_ansible.operators.tecoAnsibleOperator_2 import tecoCallAnsible2
import difflib
import base64


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




#Python Callables
###################

def goldenUpstreamConfig(ccap):

#    print ("el ccpas es:" , ccap)
#    print ("DIRECTORIO>>>>>>>>>>")
#    print (os.listdir("/usr/local/airflow/dags/cel_afijo"))

#    with open ("/usr/local/airflow/dags/cel_afijo/inventory", "r") as cmts_port_info_file:
#        cmts_port_info = cmts_port_info_file.read()
#        print (cmts_port_info)

    input_file_url = '/io/cel_afijo/tmp/cmts_port_info.json'
    with open (input_file_url, "r") as cmts_port_info_file:
        cmts_port_info = json.loads(cmts_port_info_file.read())
    for port in cmts_port_info.keys():
        cmts_port_info[port]["golden_config"] = ""      #inicializo la key golden_config para que este presente siempre
        if cmts_port_info[port]["ChannelMapPort"] == "MS-22SC-01OF-64":
            input_file_url = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/' + 'template_MS-22SC-01OF-64.j2'
            with open(input_file_url, "r") as golden_config_upstream_file:
                golden_config_upstream = golden_config_upstream_file.read()
        elif cmts_port_info[port]["ChannelMapPort"] == "MS-31SC-01OF-64":
            input_file_url = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/' + 'template_MS-31SC-01OF-64.j2'
            with open(input_file_url, "r") as golden_config_upstream_file:
                golden_config_upstream = golden_config_upstream_file.read()
        elif cmts_port_info[port]["ChannelMapPort"] == "LS-20SC-10OF-64":
            input_file_url = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/' + 'template_LS-20SC-10OF-64.j2' 
            with open(input_file_url, "r") as golden_config_upstream_file:
                golden_config_upstream = golden_config_upstream_file.read()     
        elif cmts_port_info[port]["ChannelMapPort"] == "LS-30SC-00OF-64":
            input_file_url = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/' + 'template_LS-30SC-00OF-64.j2' 
            with open(input_file_url, "r") as golden_config_upstream_file:
                golden_config_upstream = golden_config_upstream_file.read()
        elif cmts_port_info[port]["ChannelMapPort"] == "MS-31SC-00OF-64":
            input_file_url = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/' + 'template_MS-31SC-00OF-64.j2' 
            with open(input_file_url, "r") as golden_config_upstream_file:
                golden_config_upstream = golden_config_upstream_file.read()
        else:
            continue
        tm = jinja2.Template(golden_config_upstream)
        golden_config = tm.render(cmts_port_info[port])
        cmts_port_info[port]["golden_config"] = golden_config
        input_file_url = '/io/cel_afijo/tmp/cmts_port_info.json'

        with open (input_file_url, "w") as cmts_port_info_file:
            cmts_port_info_file.write(json.dumps(cmts_port_info))
    return True
                    
def search_parameters(ccap): 
    input_file_url = '/io/cel_afijo/tmp/'+ccap+'.json'
    with open (input_file_url, "r") as jason:
        combinaciones = json.load(jason )
    port_info = dict()
    for linecard in (1,2,3,6,7,8,9):
        for up_port in range (0,16):
            upstream = str(linecard) + "/0/" + str(up_port)
            for row in combinaciones:
                if row["TypePort"] == "UpStream" and row["InterfaceNamePort"] == upstream and row["NameServiceArea"] != "":
    #                port_info.append( upstream = {"ChannelMapPort":row["ChannelMapPort"]})
                    port_info[upstream] = {"ChannelMapPort": row["ChannelMapPort"],
                                           "NameServiceArea": row["NameServiceArea"],
    #                                       "RxPort": row["RxPort"],
                                            "RxPort": re.sub(r'\s+\w+', "", row["RxPort"]),
                                            "upStream": upstream,
                                            "downStream": "" # agrego el campo downStream vacio por defecto.
                                       }
                    for line in combinaciones:
                        if line["TypePort"] == "DownStream" and port_info[upstream]["NameServiceArea"] in line["NameServiceArea"] and line["HardwareEquipment"] == "Cisco-CBR8":
                            port_info[upstream]["downStream"] = line ["InterfaceNamePort"]

    print (json.dumps(port_info))
    input_file_url = '/io/cel_afijo/tmp/cmts_port_info.json'
    with open (input_file_url, "w") as cmts_port_info:
        cmts_port_info.write(json.dumps(port_info))
    return True

def targetUpstreamConfig(ccap):
    with open ("/io/cel_afijo/tmp/complience_cbr8_startup_config.bkp", "r") as configuration_file:
        configuration = configuration_file.read()
    input_file_url = '/io/cel_afijo/tmp/cmts_port_info.json'
    with open ( input_file_url , "r") as cmts_port_info_file:
        cmts_port_info = json.loads(cmts_port_info_file.read())

    for upstream in cmts_port_info.keys():
        controller = "controller Upstream-Cable " + upstream
        inicio = configuration.find(controller)
        fin = configuration.find("!", inicio)
        port_config = configuration[inicio:fin]
        print (port_config)
        cmts_port_info
        cmts_port_info[upstream]["target_config"] = port_config

    with open (input_file_url , "w") as cmts_port_info_file:
        cmts_port_info_file.write(json.dumps(cmts_port_info))

    return True

def compareUpstreamConfig(ccap):

    input_file_url = '/io/cel_afijo/tmp/cmts_port_info.json'
    with open ( input_file_url , "r") as cmts_port_info_file:
        cmts_port_info = json.loads(cmts_port_info_file.read())

    d = difflib.Differ()
    for port in cmts_port_info.keys():
        diff = d.compare( cmts_port_info[port]["golden_config"].splitlines(), cmts_port_info[port]["target_config"].splitlines())
        # output the result
        #print ("\n".join(diff))
        cmts_port_info[port]["difference"]  = "\n".join(diff)
        #cmts_port_info["difference"] = output.splitlines()
        cmts_port_info[port]["result"] = "OK"
        for row in cmts_port_info[port]["difference"].splitlines():
            if  len(row) > 0:
                if row[0] in  ("+","-","?"):
                    cmts_port_info[port]["result"] = "ERROR"
    #        print (row)
        print (port, ": ",cmts_port_info[port]["result"])

    with open (input_file_url , "w") as cmts_port_info_file:
        cmts_port_info_file.write(json.dumps(cmts_port_info))

    result = dict()

    for port in cmts_port_info.keys():
        result[port] = dict()
        result[port]["ChannelMapPort"] = cmts_port_info[port]["ChannelMapPort"]
        result[port]["NameServiceArea"] = cmts_port_info[port]["NameServiceArea"]
        result[port]["RxPort"] = cmts_port_info[port]["RxPort"]
        result[port]["upStream"] = cmts_port_info[port]["upStream"]
        result[port]["downStream"] = cmts_port_info[port]["downStream"]
        result[port]["result"] = cmts_port_info[port]["result"]

        if cmts_port_info[port]["result"] == "ERROR":
            aux = ""
            for row in cmts_port_info[port]["difference"].splitlines():
                if len(row) > 0:
                    if row[0] in ("+", "-", "?"):
                        aux += row + "\n"

            result[port]["difference"] =  aux[0:-1]
            #        result[port]["difference"] = cmts_port_info[port]["difference"]

            result[port]["target_config"] = cmts_port_info[port]["target_config"]

#   with open ("resultado.json" , "w") as resultado_json_file:
#        resultado_json_file.write(json.dumps(result))
	
    with open ("/io/cel_afijo/tmp/resultado.txt" , "w") as resultado_txt_file:
        for port in result.keys():
            to_write = port+":\n"
            resultado_txt_file.write(to_write)
            for item in result[port].keys():
                if item == "difference" or item == "target_config":
                    to_write = "  " + item + ":\n" + result[port][item] + "\n"
                    resultado_txt_file.write(to_write)

                else:
                    to_write = "  "+ item + ": " + result[port][item] + "\n"
                    resultado_txt_file.write(to_write)



#tasks
###################

t0 = DummyOperator(task_id='Init', retries=1, dag=dag)

def group(cmts, **kwargs):

    t1 = LisyQueryCustom(
        task_id='LisyQueryCombinaciones-{}'.format(cmts), 
        query_id = 'OcupacionRedHFC-VistaFisica',
        my_filter = '["","{}",""]'.format(cmts),
        dest_dir = '/io/cel_afijo/tmp/',
        file_name = '{}'.format(cmts),
        dag=dag
    )

    t2 = PythonOperator(
        task_id='Search_Parameters-'+cmts,
        python_callable=search_parameters,
        op_kwargs={ 'ccap':cmts},
        provide_context = False,
        dag=dag
    )

    t3 = PythonOperator(
        task_id='GoldenUpstreamConfig-'+cmts,
        python_callable=goldenUpstreamConfig,
        op_kwargs={ 'ccap':cmts},
        provide_context = False,
        dag=dag
    )

#    t4 = _auto_ansible = tecoCallAnsible(
#    task_id='afijo_GatteringCBR8Config', 
#    op_kwargs={
#        'Equipo_ONE':'*',
#        'pbook_dir':'/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/ansible',
#        'playbook':'afijo_GatteringCBR8Config.yaml',
#        'connection':'credenciales_equipos',
#        'inventory':'/usr/local/airflow/dags/cel_afijo/inventory',
#        'mock':False
#    },
#    dag=dag)

    t4 = tecoCallAnsible2(
                    task_id='afijo_GatteringCBR8Config', 
                    pbook_dir='/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/ansible',
                    playbook='afijo_GatteringCBR8Config.yaml',
                    connection='credenciales_equipos',
                    mock=False,
                    FILTRO_CUSTOM={'ShelfName' : "CMT1.LOR1-CBR8", 'PrePro' : "True", 'Vendor' : "Cisco"},
                    dag=dag)

    t5 = PythonOperator(    
        task_id='TargetUpstreamConfig-'+cmts,
        python_callable=targetUpstreamConfig,
        op_kwargs={ 'ccap':cmts},
        provide_context = False,
        dag=dag
    )

    t6 = PythonOperator(
        task_id='compareUpstreamConfig-'+cmts,
        python_callable=compareUpstreamConfig,
        op_kwargs={ 'ccap':cmts},
        provide_context = False,
        dag=dag
    )
   
    return t0 >> t1 >> t2 >> t3 >> t4 >> t5 >> t6


 
########################
list_cmts = ['CMT1.LOR1-CBR8']

for i in list_cmts:
    group(i)