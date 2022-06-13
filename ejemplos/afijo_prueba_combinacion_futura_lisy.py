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


#Python Callables
###################

def generoCVS (**kwargs)
    inputURL = "/io/cel_afijo/tmp/ OcupacionRedHFC_VistaFisica.json"

    with open (inputURL, "r") as  OcupacionRedHFC_VistaFisica_file:
         OcupacionRedHFC_VistaFisica = json.dumps( OcupacionRedHFC_VistaFisica_file)

#    listaFutura = get_dat.json()    # abro el arcHivo json y lo guardo en listaFutura
    # print(listaFutura)
#    with open ('requestLisy.csv','w',newline='') as f:    # lo guardo con necesitamos
#        writer=csv.DictWriter(f,listaFutura[0].keys(), delimiter=';') # lo transformo en una lista de diccionario
#        writer.writeheader()    # imprimo las columnas con su titulo
#        for lista in listaFutura:
#            writer.writerow(lista)
#            print(lista)
    
    
    
    ################################# MODELOS Equipment_Configurations_And_Combinations #####################################
    


    fila= ["Configuration", "NameEquipment", "SlotEquipment", "InterfaceNamePort", "TypePort", "StateOperationalPort", "DescriptionPort", "Mac-domainPort","RxPort", "ChannelMapPort","NameServiciAreaN"]
    
    datosLisy= ["NameEquipment", "SlotEquipment", "InterfaceNamePort", "TypePort", "OperationalState", "DescriptionPort", "Mac-Domain","RxPort", "ChannelMapPort","NameServiceArea"]
    
    listaCombinaciones = list()
    
    
    for item in   OcupacionRedHFC_VistaFisica:
        if item["TypePort"] == "DownStream": # busca DownStream dentro de TypePort
            flag = False
            for i in range (len(listaCombinaciones)):
                if item["InterfaceNamePort"] == listaCombinaciones[i][3] and item["NameEquipment"] == listaCombinaciones[i][1] and item["NameServiceArea"] != "":
                    listaCombinaciones[i][10] += "|"+ item["NameServiceArea"] # agrega | al item NameServiceArea
                    listaCombinaciones[i][10]=listaCombinaciones[i][10].lstrip("|") #quita el | de la izquierda
                    flag = True
            if flag == False: # Verifica si el puerto existe o no en la variable listaCombinaciones (sino existe lo agrega, si existe lo edita)
                aux_list = ["FUTURO"]
                for celda in datosLisy:
                    aux_list.append(item[celda])
                aux_list[10].lstrip("|")
                listaCombinaciones.append(aux_list)
    
    
    for item in   OcupacionRedHFC_VistaFisica:
        if item["TypePort"] == "UpStream":
            flag = False
            for i in range (len(listaCombinaciones)):
                if item["InterfaceNamePort"] == listaCombinaciones[i][3] and item["NameEquipment"] == listaCombinaciones[i][1] and item["NameServiceArea"] != "":
                    listaCombinaciones[i][10] += "|"+ item["NameServiceArea"]
                    listaCombinaciones[i][10]=listaCombinaciones[i][10].lstrip("|")
                    flag = True
            if flag == False:
                aux_list = ["FUTURO"]
                for celda in datosLisy:
                    aux_list.append(item[celda])
                aux_list[10].lstrip("|")
                listaCombinaciones.append(aux_list)

    csvfile = open('Equipment_Configurations_And_CombinationsSinCambios.csv', 'w', newline='')
    writercsv = csv.writer(csvfile, delimiter=';')  # obtengo un objeto csv.writer
    writercsv.writerow(fila) # lo escribo en columnas y le paso como parametros la lsita "fila"
    for row in (listaCombinaciones): # recorro todos los elementos de la consulta
        writercsv.writerow(row)  # la escribo en columnas
    
    csvfile.close()
    return True


#tasks
###################

t0 = DummyOperator(task_id='Init', retries=1, dag=dag)

query_lisy = LisyQueryCustom(
    task_id='Query_Lisy', 
    query_id = 'OcupacionRedHFC-VistaFisica',
    #my_filter = '["","{}",""]'.format(cmts),
    my_filter = '["DEV","",""]',
    dest_dir = '/io/cel_afijo/tmp/',
    file_name = ' OcupacionRedHFC_VistaFisica',
    dag=dag
    )

genero_csv = PythonOperator(
    task_id='Genero_CSV' ,
    python_callable = generoCSV,
#    op_kwargs={ 'ccap':cmts},
    provide_context = False,
    dag=dag
    )

t0 >> query_lisy >> genero_csv 