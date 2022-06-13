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
def SplitInterface(interfaz, tipo, modelo, GenMod = None):
    """Funcion que a partir de un string del tipo x/x/x genera un diccionario con placa,
        grupo y conector de un puerto de cmts 
            ----------
            Parameters
                interfaz : string
                    InterfaceName, string del tipo x/x/x
                tipo : str
                    Parametro donde se indica si el puerto de UpStream o DownStream
                    Valores validos: [UpStream, DownStream]
                modelo : str
                    Marca y modelo del CMTS. Valores Validos:
                        Cisco-CBR8
                        ARRIS-E6000
                        Casa Systems-C100G
                        ARRIS-C4
                GenMod : str
                    Generation Module. Necesario si el modelo es ARRIS-E6000. default = None

            -------
            Returns
                Dict 
                {'slot': ,'group': , 'conn': }
    """
    interface_dict = {}

    interface = interfaz.split("/")
    if tipo == 'DownStream':        
                if modelo == 'Cisco-CBR8':
                    # Placa/0/Conector
                    interface_dict['slot'] = interface[0]
                    interface_dict['conn'] = interface[2]                                      
                elif (modelo == "ARRIS-E6000" or
                        modelo == "Casa Systems-C100G" or
                        modelo == "ARRIS-C4"):
                    #para cualquiera de los 3 modelos:
                    interface_dict['slot'] = interface[0]
                    interface_dict['conn'] = interface[1]
                else:
                    raise Exception("""Modelo de CMTS no contemplado. Posibles:
                                        Cisco-CBR8
                                        ARRIS-E6000
                                        Casa Systems-C100G
                                        ARRIS-C4
                                        """)
    elif tipo == 'UpStream':
        if modelo == 'Cisco-CBR8':
            interface_dict['slot'] = interface[0]
            interface_dict['group'] = interface[1]
            interface_dict['conn'] = interface[2]
        elif modelo == "ARRIS-E6000":
            if GenMod == None or GenMod == '':
                print(GenMod)
                raise Exception("Debe especificarse Generation Module para ARRIS-E6000")
            else:						  							 																										 
                interface_dict['slot'] = interface[0]
                interface_dict['group'] = str(int(interface[1])//2) if GenMod =='2' else str(int(interface[1])//3) 
                interface_dict['conn'] = interface[1]
        elif modelo == "Casa Systems-C100G":
            interface_dict['slot'] = interface[0]
            interface_dict['group'] = interface[1]
            interface_dict['conn'] = interface[1]
        elif modelo == "ARRIS-C4":
            interface_dict['slot'] = interface[0]
            interface_dict['group'] = None
            interface_dict['conn'] = interface[1]
        else:
            raise Exception("""Modelo de CMTS no contemplado. Posibles:
                                    Cisco-CBR8
                                    ARRIS-E6000
                                    Casa Systems-C100G
                                    ARRIS-C4
                                    """)
    else:
        raise Exception("Tipo de puerto no valido. Debe ser DownStream/UpStream")    

    return interface_dict

#Python Callables
###################
def ExtraeInfo(dest_dir, file_name, shutdown=True):
    """Python callable que genera JSON con informacion de los puertos fisicos a guardar en mongoDB
        a partir del diccionario devuelto por la CustomQuery de Lisy "LisyQueryCombinaciones" 
            ----------
            Parameters
                dest_dir : str
                    Directorio donde se encuentra el JSON generado por LisyQueryCustom
                file_name : str
                    nombre del archivo JSON generado por LisyQueryCustom
                shutdown : bool
                    parametro que indica si se desea guardar info de puertos shutdown en la MongoDB
                    Si es True se guarda. Default = False  
            -------
            Returns
                None
        """
    input_file_url = dest_dir + file_name + '.json' 
    if not os.path.exists(dest_dir+ 'json4db/'):
        os.makedirs(dest_dir+ 'json4db/',mode=755, exist_ok=True)
    output_file_url = dest_dir + 'json4db/' + file_name + '4db.json'
   
    with open(input_file_url, 'r') as inputfile:
        interfaces = json.load(inputfile)

    outputfile = open(output_file_url, 'w')
    coleccion = []

    for interface_x in interfaces:
        documento = {} #Debe crearse por cada iteracion. Si no cada item de la lista apunta a un mismo diccionario en memoria
 
        #print(interface_x) #Debug purposes       
        if interface_x['OperationalState']=='Active':
            if interface_x['TypePort'] == 'DownStream':
                documento['cmts'] = interface_x['NameEquipment']
                documento['mgt'] = interface_x['NameServiceArea']
                documento['mac_domain'] = interface_x['Mac-Domain']
                
                interface = SplitInterface(interface_x['InterfaceNamePort'],interface_x['TypePort'],interface_x['HardwareEquipment'],interface_x['GenerationModule'])
                documento['dw_slot'] = interface['slot']
                documento['dw_conn'] = interface['conn']                                      
                               
                documento['dw_channel_map'] = interface_x['ChannelMapPort']
                #coleccion.append(documento) #Debug Purposes

                #Busco el upstream perteneciente a la combinacion:
                for interface_up in interfaces:
                    if interface_up['TypePort'] == 'UpStream':
                        if interface_up['Mac-Domain'] == interface_x['Mac-Domain']:
                            if interface_up['NameServiceArea'] == interface_x['NameServiceArea']:
                                interface = SplitInterface(interface_up['InterfaceNamePort'],interface_up['TypePort'],interface_up['HardwareEquipment'],interface_up['GenerationModule'])      # Placa/0/Conector
                                documento['up_slot'] = interface['slot']
                                documento['up_group'] = interface['group']
                                documento['up_conn'] = interface['conn']
                                
                                documento['up_channel_map'] = interface_up['ChannelMapPort']
                                documento['up_power'] = interface_up['RxPort']
                            else:
                                print("ATENCION: Mismo MAC-Domain, distinto MGT:", interface_up)
                print("documento-comb:", documento)
                coleccion.append(documento)
                #print(coleccion) #Debug Purposes
        elif shutdown == True:
            if interface_x['OperationalState']=='Available': #Deberia ser siempre True, si no, falta definir campo en Lisy
                if interface_x['Mac-Domain']  != '': #A fines del compliance solo interesan los que esten configurados
                    documento['cmts'] = interface_x['NameEquipment']
                    documento['mac_domain'] = interface_x['Mac-Domain'] 
                    if interface_x['TypePort'] == 'DownStream':
                        interface = SplitInterface(interface_x['InterfaceNamePort'],interface_x['TypePort'],interface_x['HardwareEquipment'],interface_x['GenerationModule'])
                        documento['dw_slot'] = interface['slot']
                        documento['dw_conn'] = interface['conn']
                        documento['dw_channel_map'] = interface_x['ChannelMapPort']
                    else:
                        interface = SplitInterface(interface_x['InterfaceNamePort'],interface_x['TypePort'],interface_x['HardwareEquipment'],interface_x['GenerationModule'])   
                        documento['up_slot'] = interface['slot']
                        documento['up_group'] = interface['group']
                        documento['up_conn'] = interface['conn']
                        documento['up_channel_map'] = interface_x['ChannelMapPort']
                        #documento['up_power'] = interface_x['RxPort'] #No definido para el caso, borrar?
                    #print("documento-nocomb:", documento) #Debug purposes
                    coleccion.append(documento)
                else:
                    print("ATENCION: Puerto Available, sin mac domain configurado")
                    print(interface_x)
            else:
                print("ERROR de LISY, puerto sin estado")
    print("coleccion final")
    print(coleccion)
    json.dump(coleccion,outputfile)
                       
#tasks
###################
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
    task_id='GeneraJson4Mongo'+cmts,
    python_callable=ExtraeInfo,
    op_kwargs={'dest_dir':'/io/cel_afijo/tmp/', 'file_name':cmts, 'shutdown':True},
    provide_context = False,
    dag=dag
    )

    t3 = TecoMongoDb(
        task_id='Push2MongoDB',
        source_files='*',
        source_dir='/io/cel_afijo/tmp/json4db',
        table="CMTS-PuertosFisicos",
        sorce_datatype='json',
        provide_context=False,
        dag=dag
    )

    return t0 >> t1 >> t2 >> t3


#################################
t0 = DummyOperator(task_id='dummy_task', retries=1, dag=dag)


########################
list_cmts = ['CMT4.ITU1-CBR8', 'CMT1.ALM1-E6K', 'CMT1.AVA1-CBR8', 'CMT1.JMA1-C100G', 'CMT1.SNW1-C4' ]
#list_cmts = ['CMT5.ALM1-CBR8']

for i in list_cmts:
    group(i)
