"""
Este DAG realiza el parseo de puertos físicos y lógicos de CBR8 para el compliance contra Lisy

"""
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from lisy_plugin.operators.lisy_operator import *
from datetime import datetime, timedelta
from tabulate import tabulate
from pprint import pprint
from os import strerror
import os
import os.path
import glob
import sys
import textfsm
import math
import json
import pymongo
import subprocess

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
# Args
default_args = {
    'owner': 'afijo',
    'depends_on_past': False,
    'start_date': datetime(2021, 9, 8),
    'email': ['automation@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}

# Dag
dag = DAG(
    dag_id=DAG_ID, 
    schedule_interval= None, 
    default_args=default_args,
    tags=["COMPLIANCE","CMTS","LISY"]
)

#Functions 
###################
def SplitInterface(interfaz, tipo, modelo, GenMod = None) -> dict:
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
                #print(GenMod)
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
    """Python callable que genera JSON con informacion de los puertos fisicos+logicos a guardar en mongoDB
        a partir del diccionario devuelto por la CustomQuery de Lisy "LisyQueryCombinaciones" y su posterior
        combinacion con la info de channel map almacenada en mongo a través de form.io
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
    #os.system('rm '+dest_dir+'*')
    input_file_url = dest_dir + file_name + '.json' 
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir,mode=755, exist_ok=True)
    #output_file_url = dest_dir + 'json4db/' + file_name + '4db.json'
    output_file_url = '/io/cel_afijo/tmp/CompliancePuertosLisy/' + file_name + '4db.json'
    
    print("Abriendo json con info extraida de Lisy: ", end=" ")
    print(input_file_url)
    try:
        with open(input_file_url, 'r') as inputfile:
            interfaces = json.load(inputfile)
    except:
        print("No se pudo abrir", input_file_url)
        print("Generando Excepcion...")
        raise("No se pudo abrir"+input_file_url)
    outputfile = open(output_file_url, 'w')
    coleccion = []

    #Conexión contra MongoDB Form.IO
    #El operador TecoReadMongo solo permite leer desde la DB Tambo, debo leer de formio
    #Utilizo directamente pymongo
    HOST = 'tambo_mongodb'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    mDb = mCli["formio"]
    mColForm = mDb["forms"]


    for interface_x in interfaces:
        documento = {} #Debe crearse por cada iteracion. Si no cada item de la lista apunta a un mismo diccionario en memoria
 
        #print(interface_x) #Debug purposes       
        if interface_x['OperationalState']=='Active' and interface_x['StateServiceArea']=='Active':
            if interface_x['TypePort'] == 'DownStream':
                documento['cmts'] = interface_x['NameEquipment']
                documento['mgt'] = interface_x['NameServiceArea']
                documento['mac_domain'] = interface_x['Mac-Domain']
                
                interface = SplitInterface(interface_x['InterfaceNamePort'],interface_x['TypePort'],interface_x['HardwareEquipment'],interface_x['GenerationModule'])
                documento['dw_slot'] = interface['slot']
                documento['dw_conn'] = interface['conn']                                      
                                           
                x = mColForm.find_one({'path':"dwchannelmaps"}) #obtengo id del formulario en mongo
            
                filter={
                    'form': (x['_id']), #utilizo el id para traerme todo lo del formulario
                    'deleted': None,
                    'data.channelMapName': interface_x['ChannelMapPort']
                }

                result = mCli['formio']['submissions'].find_one(
                filter=filter,
                )

                if result == None:
                    raise Exception(f"DW Channel Map no definido en DB: {interface_x['ChannelMapPort']}")
                    #print(f"DW Channel Map no definido en DB: {interface_x['ChannelMapPort']}")
                else:
                    #print(result)
                    documento['dw_channels'] = []
                    for portadora in result['data']['portadoras']:
                        documento['dw_channels'].append({'freq_cen':portadora['freq_central'], 'mod':portadora['mod'].replace(" ",""), 'BW':portadora['BW']})

                #Busco el upstream perteneciente a la combinacion:
                for interface_up in interfaces:
                    if interface_up['TypePort'] == 'UpStream':
                        if interface_up['Mac-Domain'] == interface_x['Mac-Domain']:
                            if interface_up['NameServiceArea'] == interface_x['NameServiceArea']:
                                interface = SplitInterface(interface_up['InterfaceNamePort'],interface_up['TypePort'],interface_up['HardwareEquipment'],interface_up['GenerationModule'])      # Placa/0/Conector
                                documento['up_slot'] = interface['slot']
                                documento['up_group'] = interface['group']
                                documento['up_conn'] = interface['conn']
                                
                                #documento['up_channel_map'] = interface_up['ChannelMapPort']

                                #Cruzo informacion con channel maps
                                #JoinChMap(interface_up['ChannelMapPort'], 'up')


                                x = mColForm.find_one({'path':"upchannelmaps"}) #obtengo id del formulario en mongo
                            
                                filter={
                                    'form': (x['_id']), #utilizo el id para traerme todo lo del formulario
                                    'deleted': None,
                                    'data.channelMapName': interface_up['ChannelMapPort']
                                }

                                result = mCli['formio']['submissions'].find_one(
                                filter=filter,
                                )

                                if result == None:
                                    raise Exception(f"UP Channel Map no definido en DB: {interface_up['ChannelMapPort']}")
                                    #print(f"UP Channel Map no definido en DB: {interface_up['ChannelMapPort']}")
                                else:
                                    #print(result)
                                    documento['up_channels'] = []
                                    flag = False
                                    for portadora in result['data']['portadoras']:
                                        #print("portadora: ", portadora['freq_central'])
                                        if len(documento['up_channels']) != 0: #si no está vacia la lista
                                            for elemento in documento['up_channels']: #recorro portadoras ya registradas
                                                #print("comparo ", portadora['freq_central'], "con ", elemento['freq_cen'])
                                                if portadora['freq_central'] == elemento['freq_cen']: #Ya registré la portadora? (Caso C4)
                                                    flag = True
                                                    #print("seteo flag")
                                            if not flag:
                                                documento['up_channels'].append({'freq_cen':portadora['freq_central'], 'mod':portadora['mod'].replace(" ",""), 'BW':portadora['BW'], 'up_power':interface_up['RxPort'].split()[0]})
                                                #print("guardo")
                                            flag = False
                                            #print("limpio el flag")
                                        else:
                                            #print(interface_x)
                                            #print(interface_up)
                                            #print(interface_up['RxPort'])
                                            try:
                                                #print(interface_up['RxPort'].split()[0])
                                                documento['up_channels'].append({'freq_cen':portadora['freq_central'], 'mod':portadora['mod'].replace(" ",""), 'BW':portadora['BW'], 'up_power':interface_up['RxPort'].split()[0]})
                                            except (IndexError):
                                                print("Potencia no definida en Lisy, campo vacío")

                                #documento['up_power'] = interface_up['RxPort']
                            else:
                                print("ATENCION: Mismo MAC-Domain, distinto MGT:", interface_up)
                #print("documento-comb:", documento)
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
                        #documento['dw_channel_map'] = interface_x['ChannelMapPort']
                        #Cruzo informacion con channel maps
                        #JoinChMap(interface_x['ChannelMapPort'], 'down')
                        
                        x = mColForm.find_one({'path':"dwchannelmaps"}) #obtengo id del formulario en mongo
                    
                        filter={
                            'form': (x['_id']), #utilizo el id para traerme todo lo del formulario
                            'deleted': None,
                            'data.channelMapName': interface_x['ChannelMapPort']
                        }

                        result = mCli['formio']['submissions'].find_one(
                        filter=filter,
                        )

                        if result == None:
                            raise Exception(f"DW Channel Map no definido en DB: {interface_x['ChannelMapPort']}")
                            #print(f"DW Channel Map no definido en DB: {interface_x['ChannelMapPort']}")
                        else:
                            #print(result)
                            documento['dw_channels'] = []
                            for portadora in result['data']['portadoras']:
                                documento['dw_channels'].append({'freq_cen':portadora['freq_central'], 'mod':portadora['mod'].replace(" ",""), 'BW':portadora['BW']})

                    else:
                        interface = SplitInterface(interface_x['InterfaceNamePort'],interface_x['TypePort'],interface_x['HardwareEquipment'],interface_x['GenerationModule'])   
                        documento['up_slot'] = interface['slot']
                        documento['up_group'] = interface['group']
                        documento['up_conn'] = interface['conn']
                        #documento['up_channel_map'] = interface_x['ChannelMapPort']
                        #Cruzo informacion con channel maps
                        #JoinChMap(interface_x['ChannelMapPort'], 'up')


                        x = mColForm.find_one({'path':"upchannelmaps"}) #obtengo id del formulario en mongo
                    
                        filter={
                            'form': (x['_id']), #utilizo el id para traerme todo lo del formulario
                            'deleted': None,
                            'data.channelMapName': interface_x['ChannelMapPort']
                        }

                        result = mCli['formio']['submissions'].find_one(
                        filter=filter,
                        )

                        if result == None:
                            raise Exception(f"UP Channel Map no definido en DB: {interface_x['ChannelMapPort']}")
                            #print(f"UP Channel Map no definido en DB: {interface_x['ChannelMapPort']}")
                        else:
                            #print(result)
                            documento['up_channels'] = []
                            for portadora in result['data']['portadoras']:
                                documento['up_channels'].append({'freq_cen':portadora['freq_central'], 'mod':portadora['mod'].replace(" ",""), 'BW':portadora['BW']})
                       
                        #documento['up_power'] = interface_x['RxPort'] #No definido para el caso, borrar?
                    #print("documento-nocomb:", documento) #Debug purposes
                    coleccion.append(documento)
                else:
                    print("ATENCION: Puerto Available, sin mac domain configurado")
                    print(interface_x)
            else:
                print("ERROR de LISY, puerto sin estado")
    #print("coleccion final")
    #print(coleccion)
    json.dump(coleccion,outputfile)

#Python callable para Seleccion de Parser
def Select_Parser(dest_dir,cmts):
    if cmts.endswith("C100G"):
        C100G_Port_Parser(dest_dir, cmts)
    elif cmts.endswith("CBR8"):
        CBR8_Port_Parser(dest_dir, cmts)
    elif cmts.endswith("E6K"):
        E6K_Port_Parser(dest_dir, cmts)
    else:
        raise Exception("Modelo de CMTS no contemplado:", cmts)

# Python callable Parseo Config E6K
def E6K_Port_Parser(dest_dir, cmts):

    print("Preparando Parseo de", cmts)
    template_e6k_ofdma = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_Parser_E6K_ofdma.fsm'
    template_e6k_up = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_Parser_E6K_up.fsm'
    template_e6k_dw = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_E6Kparserdw.fsm'
    template_e6k_mp = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_Parser_profile.fsm'
    template_e6k_no_shut = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_parserE6Knoshut.fsm'

    print("Buscando archivos de BackUp para", cmts)
    list_of_files = glob.glob('/io/cel_core/backup/CMTS/'+cmts+'/configs/*.bkp') #Busca todos los BackUps del CMTS "file_name"
    print("Archivos encontrados:")
    for archivo in list_of_files:
        print("\t",archivo,sep="")

    if len(list_of_files) > 0:
        backup = max(list_of_files, key=os.path.getctime) # Toma el ultimo BackUp de la lista 
        print("Archivo seleccionado(latest):")
        print("\t",backup)
    else:
        print("\tNo se encontraron archivos de BackUp para", cmts)
        print("\tGenerando Excepción")
        raise Exception("No existen archivos de BackUp para "+cmts)

    
    cat = subprocess.Popen(
        ['cat', backup],
        stdout=subprocess.PIPE)
    sed = subprocess.Popen(
        ['sed','-n', '/^interface cable-upstream /,/exit/p'],
        stdin=cat.stdout,
        stdout=subprocess.PIPE)

    end_of_pipe = sed.stdout
    backup_snippet=""
    for line in end_of_pipe:
        backup_snippet += line.decode('utf-8')
    

    with open(template_e6k_up) as fu:
        # Parseo UP QAM
        print("Parseando portadoras upstream QAM de", cmts,"...")
        re_tableu = textfsm.TextFSM(fu) # Levanto el template de upstream
        headerup = re_tableu.header
        resultup = re_tableu.ParseText(backup_snippet)
        print("Resultado del parseo de Upstream:")
        print(tabulate(resultup, headers=headerup))
    
    with open(template_e6k_ofdma) as fu:
        # Parseo UP OFDMA
        print("Parseando portadoras upstream OFDMA de", cmts,"...")
        re_tableu = textfsm.TextFSM(fu) # Levanto el template de upstream
        headeru = re_tableu.header
        resultOfdma = re_tableu.ParseText(backup_snippet)
        print("Resultado del parseo Upstreams OFDMA:")
        print(tabulate(resultOfdma, headers=headeru))

    with open(template_e6k_mp) as fu:
        # Parseo Modulation Profiles
        print("Parseando portadoras upstream OFDMA de", cmts,"...")
        re_tableu = textfsm.TextFSM(fu) # Levanto el template de upstream
        headeru = re_tableu.header
        resultuModProfile = re_tableu.ParseText(backup_snippet)
        print("Resultado del parseo Upstreams Modulation Profile:")
        print(tabulate(resultuModProfile, headers=headeru))

    cat = subprocess.Popen(
        ['cat', backup],
        stdout=subprocess.PIPE)
    sed = subprocess.Popen(
        ['sed','-n', '/shutdown/,/exit/p'],
        stdin=cat.stdout,
        stdout=subprocess.PIPE)

    end_of_pipe = sed.stdout
    backup_snippet=""
    for line in end_of_pipe:
        backup_snippet += line.decode('utf-8')
    #print('Included files: ', backup_snippet)


    with open(template_e6k_no_shut) as fu:
        #Parseo Admin Status
        print("Parseando Admin Status de las portadoras...")
        re_tableu = textfsm.TextFSM(fu) # Levanto el template de upstream
        headeru = re_tableu.header
        resultAdmSt = re_tableu.ParseText(backup_snippet)
        print("Resultado del parseo Estado administrativo:")
        print(tabulate(resultAdmSt, headers=headeru))
    #adminstatus_dict = [dict(zip(headeru, pr)) for pr in resultu]
    #print(json.dumps(adminstatus_dict, indent=4))

    upInfo = list()
    
    for row in resultOfdma:
        if row [4] != "":
            aux = row
            aux[7] = str(int(row[7])-int(row[6]))
            aux[6] = str(round(int(aux[7])/2+int(row[6])))
            resultup.append(aux)
    for item in resultup:
        for row in resultuModProfile:
            item[1] = item[0][0]
            #print (resultup[1])
            #print (row)
            if item[0] == row[0]:
                item.append(row[1])
                item.append ("")
        for row in resultAdmSt:
            if item[0] == row[0]:
                item[9] = row[3]
        if item[8] == "64":
            item[8] = "64QAM"
        elif item[8] == "20":
            item[8] = "16QAM" 
        elif item[8] == "24":
            item[8] = "OFDMA" 

        if item[9] == "no shutdown" and item[4] != "": 
            upInfo.append(item)
    #headerup.append("profile")
    #headerup.append("adm_status")
    #print("Resultado del parseo Upstreams Modulation Profile:")
    #print(tabulate(upInfo, headers=headerup))

    cat = subprocess.Popen(
        ['cat', backup],
        stdout=subprocess.PIPE)
    sed = subprocess.Popen(
        ['sed','-n', '/^interface cable-downstream /,/exit/p'],
        stdin=cat.stdout,
        stdout=subprocess.PIPE)

    end_of_pipe = sed.stdout
    backup_snippet=""
    for line in end_of_pipe:
        backup_snippet += line.decode('utf-8')

    #print('Included files: ', backup_snippet)

    with open(template_e6k_dw) as fu:
        # Parseo DW
        print("Parseando portadoras downstream QAM/OFDM de", cmts,"...")
        re_tableu = textfsm.TextFSM(fu) # Levanto el template de upstream
        headerup = re_tableu.header
        resultdown = re_tableu.ParseText(backup_snippet)
        print("Resultado del parseo downstream:")
        print(tabulate(resultdown, headers=headerup))
        #print (resultu)

    print("Procesando información parseada...")
    dwInfo = list()

    for i in range(len(resultdown)):
        if resultdown[i][1] == "cable":
            resultdown[i][4] = "256QAM"
            resultdown[i][5] = "6000000"
        elif resultdown[i][1] == "ofdm":
            resultdown[i][4] = "OFDM" 
            resultdown[i][5] = str(int(resultdown[i][7]) - int(resultdown[i][6]))
            resultdown[i][3] = str(round(int(resultdown[i][5])/2+int(resultdown[i][6])))
        for row in resultAdmSt:
            if row [0] == resultdown[i][0]:
                dwInfo.append(resultdown[i])

    print(tabulate(dwInfo, headers=headerup))
		
    combinationsInfo = dict ()
    for row in upInfo:
        if row[1] not in combinationsInfo.keys():
            combinationsInfo[row[1]]=dict()
        if row[2] not in combinationsInfo[row[1]].keys():
            aux = row[0].split("/")
            dwaux = row[3].split("/")
            combinationsInfo[row[1]][row[2]] = {"cmts": cmts,
                "mac_domain": row[4],
                "dw_channels": [],
                "up_slot": row[1],
                "up_group": aux[1],
                "up_conn": row[2],
                "up_channels": [],
                "dw_conn": dwaux[0],
                "dw_slot": dwaux[1]
            }

    for slot in combinationsInfo.keys():
        for port in combinationsInfo[slot].keys():
            for row in upInfo:
                if row[1] == slot and row[2] == port:
                    combinationsInfo[slot][port]["up_channels"].append({"BW": row[7], 
                        "freq_cen": row[6],
                        "up_power": row[5],
                        "mod": row[8]})
            for drow in dwInfo:
                if drow[2] == combinationsInfo[slot][port]["mac_domain"]:
                    combinationsInfo[slot][port]["dw_channels"].append({
                        "mod": drow[4],
                        "BW": drow[5],
                        "freq_cen": drow[3]
                    })

    #print (json.dumps(combinationsInfo, indent=4))

    list_output_final_con_tuti = list()
    for slot in combinationsInfo.keys():
        for port in combinationsInfo[slot].keys():
            list_output_final_con_tuti.append(combinationsInfo[slot][port])

    print("Generando archivo de salida:",dest_dir+cmts+".json")
    output_file_url = dest_dir + cmts + '.json'
    #print("Salida:", list_output_final_con_tuti)
    with open(output_file_url, 'w') as outputfile:
        json.dump(list_output_final_con_tuti, outputfile)

# Python callable Parseo Config C100G
def C100G_Port_Parser(dest_dir, cmts):
    print("Preparando Parseo de", cmts)
    template_c100g_md = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_ParserC100GMD.fsm'
    template_c100g_up = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_ParserC100GUP.fsm'
    template_c100g_dw = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_ParserC100GDW.fsm'
    template_c100g_mp = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_ParserC100GMP.fsm'

    print("Buscando archivos de BackUp para", cmts)
    list_of_files = glob.glob('/io/cel_core/backup/CMTS/'+cmts+'/configs/*.bkp') #Busca todos los BackUps del CMTS "file_name"
    print("Archivos encontrados:")
    for archivo in list_of_files:
        print("\t",archivo,sep="")

    if len(list_of_files) > 0:
        backup = max(list_of_files, key=os.path.getctime) # Toma el ultimo BackUp de la lista 
        print("Archivo seleccionado(latest):")
        print("\t",backup)
    else:
        print("\tNo se encontraron archivos de BackUp para", cmts)
        print("\tGenerando Excepción")
        raise Exception("No existen archivos de BackUp para "+cmts)


    try:
        print("Abriendo BackUp y Templates...")
        with open(template_c100g_dw) as fd,  open(template_c100g_up) as fu, open(template_c100g_md) as fmd, open(template_c100g_mp) as fmp, open(backup) as input:
            data = input.read()
            
            # Parseo Mac Domain
            print("Iniciando parseo de Mac Domains...")
            re_table_md = textfsm.TextFSM(fmd) # Levanto el template del MD
            header_md = re_table_md.header
            result_md = re_table_md.ParseText(data) # Parseo el backup con el template 'template_c100g_md'
            print("Resultado del parseo MacDomains:")
            print(tabulate(result_md, headers=header_md))
            mac_domains_dict = [dict(zip(header_md, pr)) for pr in result_md]

            # Parseo UP
            print("Iniciando parseo de portadoras UP...")
            re_tableu = textfsm.TextFSM(fu) # Levanto el template de upstream
            headeru = re_tableu.header
            resultu = re_tableu.ParseText(data) # Parseo el backup con el template 'template_c100g_up'
            print("Resultado del parseo Upstream:")
            print(tabulate(resultu, headers=headeru))
            upstreams_dict = [dict(zip(headeru, pr)) for pr in resultu]

            # Parseo DW
            print("Iniciando parseo de  portadoras DW...")
            re_tabled = textfsm.TextFSM(fd) # Levanto el template de upstream
            headerd = re_tabled.header
            resultd = re_tabled.ParseText(data) # Parseo el backup con el template 'template_c100g_up'
            print("Resultado del parseo Downstreams:")
            print(tabulate(resultd, headers=headerd))
            downstreams_dict = [dict(zip(headerd, pr)) for pr in resultd]

            # Parseo Mod Profile
            print("Iniciando parseo de Modulation profiles...")
            re_table_mp = textfsm.TextFSM(fmp) # Levanto el template del MP
            header_mp = re_table_mp.header
            result_mp = re_table_mp.ParseText(data) # Parseo el backup con el template 'template_c100g_md'
            print("Resultado del parseo ModProfiles:")
            print(tabulate(result_mp, headers=header_mp))
            mod_profiles_dict = [dict(zip(header_mp, pr)) for pr in result_mp]

            #Armado de salida
            print("Generando lista de diccionarios con info parseada...")
            lista_salida = []

            salida={}
            salida['mac_domain'] = 'inicial'

            new_salida={}
            new_salida['up_conn']= 'inicial'
            flag_new_salida = False

            for portadora in mac_domains_dict:
                print("\tAnalizando portadora:")
                print("\t\t",portadora,sep="")
                #Chequeo si comienzo a recorrer otro mac_domain
                if portadora['mac_domain'] != salida['mac_domain']:
                    if salida['mac_domain'] != 'inicial':
                        print("\tDistinto MacDomain!")
                        print("#################################################################")
                        print("Guardando Combinacion anterior:")
                        print(salida)
                        print("#################################################################")
                        lista_salida.append(salida)

                        if flag_new_salida:
                            print("#################################################################")
                            print("Guardando Combinacion anterior: (mismo MD, distinto up conn")
                            print(new_salida)
                            print("#################################################################")
                            lista_salida.append(new_salida.copy()) #Debe hacerse copy para que no sea modificado en la lista
                                                                    #Lo que inserta en la lista es un puntero al diccionario
                            flag_new_salida = False
                            new_salida['up_conn']= 'inicial'

                    print("Preparando registro de nueva combinacion...")
                    salida={}
                    salida['cmts'] = cmts
                    salida['mac_domain'] = portadora['mac_domain']
                    salida['up_channels'] = []
                    salida['dw_channels'] = []
                    if portadora['upstream'] != '':
                        salida['up_slot'] = portadora['upstream'].split('/')[0]
                        salida['up_conn'] = portadora['upstream'].split('/')[1].split('.')[0]
                        salida['up_group'] = salida['up_conn']

                        for up in upstreams_dict:
                            if up['upstream'] == salida['up_slot']+'/'+portadora['upstream'].split('/')[1]:
                                print("\t\tupstream identificado")
                                dicc = {}
                                dicc['freq_cen'] = up['frequency']
                                dicc['BW'] = up['bw']
                                dicc['up_power'] = up['power']
                                for profile in mod_profiles_dict:
                                    if profile['mp'] == up['mp']:
                                        dicc['mod'] = profile['shortmod'].upper()
                                print("\t\tRegistrando portadora:", dicc)
                                salida['up_channels'].append(dicc)
                                print("Combinacion temp: ",salida,sep="")

                    #Por el orden de las config en el cmts nunca llega a la siguiente porcion de código
                    if portadora['downstream'] != '':
                        salida['dw_slot'] = portadora['downstream'].split('/')[0]
                        salida['dw_conn'] = portadora['downstream'].split('/')[1]
                        #print(portadora['downstream'])

                        for down in downstreams_dict:
                            if down['downstream'] == salida['dw_slot']+'/'+salida['dw_conn']:
                                if portadora['downstream'].split('/')[2] == down['channel']:
                                    #print("upstream encontrado")
                                    dicc = {}
                                    
                                    if down['frequency'] != '' and portadora['mod'] == 'qam':
                                        print("downstream QAM identificado")
                                        dicc = {}                                                                 
                                        dicc['mod'] = "256QAM"
                                        dicc['BW'] = "6000000"
                                        dicc['freq_cen'] = down['frequency']

                                        #print("mac domain same",portadora)
                                        print("\t\tRegistrando portadora:",dicc)
                                        new_salida['dw_channels'].append(dicc)
                                        salida['dw_channels'].append(dicc)
                                        #print("\tnew_salida",new_salida)
                                        print("\tsalida",salida)

                                    elif down['frequency'] == '' and portadora['mod'] == 'ofdm':
                                        print("downstream OFDM identificado")
                                        dicc = {}
                                        dicc['mod'] = "OFDM"
                                        dicc['BW'] = str(int(down['finfrec']) - int(down['inifrec']) + 2000000) #1MHZ de guarda por cada lado
                                        dicc['freq_cen'] = str((int(down['finfrec']) + int(down['inifrec']))//2)
                                    
                                        #print("mac domain same",portadora)
                                        print("\t\tRegistrando portadora:",dicc)
                                        new_salida['dw_channels'].append(dicc)
                                        salida['dw_channels'].append(dicc)
                                        #print("\tnew_salida",new_salida)
                                        print("\tsalida",salida)
                ###################################FIN de la parte de codigo que no llega nunca######################################
                else:
                    if portadora['upstream'] != '':
                        if salida['up_conn'] == portadora['upstream'].split('/')[1].split('.')[0]:
                            for up in upstreams_dict:
                                if up['upstream'] == salida['up_slot']+'/'+portadora['upstream'].split('/')[1]:
                                    print("\t\tupstream identificado")
                                    dicc = {}
                                    dicc['freq_cen'] = up['frequency']
                                    dicc['BW'] = up['bw']
                                    dicc['up_power'] = up['power']
                                    for profile in mod_profiles_dict:
                                        if profile['mp'] == up['mp']:
                                            dicc['mod'] = profile['shortmod'].upper()
                                    print("\t\tRegistrando portadora:", dicc)
                                    salida['up_channels'].append(dicc)
                                    print("\tCombinacion temp:",salida)
                        else: #mismo mac domain, distinto up
                            #mac domain compartido por dos nodos
                            print("\t\tMismo MacDomain, distinto up conn")
                            flag_new_salida = True
                            if new_salida['up_conn'] != portadora['upstream'].split('/')[1].split('.')[0]:
                                new_salida=salida.copy() #Conservo datos dw si existiesen

                                new_salida['up_channels'] = [] 
                                new_salida['up_slot'] = portadora['upstream'].split('/')[0]
                                new_salida['up_conn'] = portadora['upstream'].split('/')[1].split('.')[0]
                                new_salida['up_group'] = new_salida['up_conn']
                            for up in upstreams_dict:
                                if up['upstream'] == new_salida['up_slot']+'/'+portadora['upstream'].split('/')[1]:
                                    print("\t\tupstream identificado")
                                    dicc = {}
                                    dicc['freq_cen'] = up['frequency']
                                    dicc['BW'] = up['bw']
                                    dicc['up_power'] = up['power']
                                    for profile in mod_profiles_dict:
                                        if profile['mp'] == up['mp']:
                                            dicc['mod'] = profile['shortmod'].upper()
                                    print("\tRegistrando portadora:", dicc)
                                    new_salida['up_channels'].append(dicc)
                                    print("new salida:",new_salida)
                                    print("Info acumumulada:",salida)

                    if portadora['downstream'] != '':
                        if new_salida.get('dw_slot') == None or salida.get('dw_slot') == None: #Aun no se habia cargado Salida
                            salida['dw_slot'] = new_salida['dw_slot'] = portadora['downstream'].split('/')[0]
                            salida['dw_conn'] = new_salida['dw_conn'] = portadora['downstream'].split('/')[1]
                            new_salida['dw_channels'] = []

                        for down in downstreams_dict:
                            if down['downstream'] == new_salida['dw_slot']+'/'+new_salida['dw_conn']:
                                if portadora['downstream'].split('/')[2] == down['channel']:
                                    #Primero busco solo las QAM
                                    if down['frequency'] != '' and portadora['mod'] == 'qam':
                                        print("\t\tdownstream QAM identificado")
                                        dicc = {}                                                                 
                                        dicc['mod'] = "256QAM"
                                        dicc['BW'] = "6000000"
                                        dicc['freq_cen'] = down['frequency']
                                        print("\t\tRegistrando portadora:",dicc)
                                        new_salida['dw_channels'].append(dicc) #Potencial combinacion distinta (mismo dw, distinto up)
                                        salida['dw_channels'].append(dicc)
                                        #print("\tnew_salida",new_salida)
                                        print("\tCombinacion temp",salida)

                                    elif down['frequency'] == '' and portadora['mod'] == 'ofdm':
                                        print("\t\tdownstream OFDM encontrado")
                                        dicc = {}
                                        dicc['mod'] = "OFDM"
                                        dicc['BW'] = str(int(down['finfrec']) - int(down['inifrec']) + 2000000) #1MHZ de guarda por cada lado
                                        dicc['freq_cen'] = str((int(down['finfrec']) + int(down['inifrec']))//2)
                                        print("\t\tRegistrando portadora:",dicc)
                                        new_salida['dw_channels'].append(dicc)
                                        salida['dw_channels'].append(dicc)
                                        #print("\tnew_salida",new_salida)
                                        print("\tCombinacion temp",salida)

            
            output_file_url = dest_dir + cmts + '.json'
            print("Generando archivo de salida: ", output_file_url)
            #print("Salida:", lista_salida)
            with open(output_file_url, 'w') as outputfile:
                json.dump(lista_salida,outputfile)
            outputfile.close()
    except:
        raise Exception("Ocurrió un error garrafal!")

# Python callable Parseo Config CBR8
def CBR8_Port_Parser(dest_dir, cmts):
    #os.system('rm '+dest_dir+'*')
    template_cbr8_up = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_ParserCBR8UP.fsm'
    template_cbr8_dw = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_ParserCBR8DW.fsm'
    template_cbr8_mp = '/usr/local/airflow/dags/cel_afijo/CompliancePuertosCMTS/templates/afijo_ParserCBR8MP.fsm'
    list_of_files = glob.glob('/io/cel_core/backup/CMTS/'+cmts+'/configs/*.bkp') #Busca todos los BackUps del CMTS "file_name"
    print("Lista de todos los back up: ",list_of_files)
    #
    # Añadir Excepcion o aviso en caso de falla al abrir el archivo
    #
    if len(list_of_files) > 0:
        backup = max(list_of_files, key=os.path.getctime) # Toma el ultimo BackUp de la lista 
        print("Archivo seleccionado(latest):")
        print("\t",backup)
        with open(template_cbr8_up) as fu, open(template_cbr8_dw) as fd, open(template_cbr8_mp) as fmp, open(backup) as input:
            data = input.read()
            #print(data)
            # Parseo Mod Profile
            re_table_mp = textfsm.TextFSM(fmp) # Levanto el template del MP
            header_mp = re_table_mp.header 
            result_mp = re_table_mp.ParseText(data) # Parseo el backup con el template 'template_cbr8_mp'
            mod_profiles = {}
            #print("Parseo de Mod Profiles:\n", result_mp) #Debug Purposes
            for mp in result_mp: # Se completa el diccionario de los MP
                clave = mp[0]
                valor = mp[1]
                if clave not in mod_profiles:
                    mod_profiles[clave] = valor
                else:
                    if mod_profiles[clave]=='':
                       mod_profiles[clave] = valor
            for mp in mod_profiles.items():
                if mp[1] == '':
                    mod_profiles[mp[0]] = 'OFDMA'
            #print("Salida de Mod Profiles:\n", mod_profiles) #Debug Purposes
            # Parseo UP
            re_tableu = textfsm.TextFSM(fu) # Levanto el template de upstream
            headeru = re_tableu.header
            resultu = re_tableu.ParseText(data) # Parseo el backup con el template 'template_cbr8_up'
            salida_up = [dict(zip(headeru, pr)) for pr in resultu] # Creo una lista de diccionarios UP
            up_salida = []
            dic_interface_up = {}
            up_interfaceprev = '0'
            for dic in salida_up: 
                up_slot = dic['interface'].split('/')[0]
                up_conn = dic['interface'].split('/')[2]
                dw_conn = int(math.floor(int(up_conn)/2)) 
                mac_domain = up_slot+'/0/'+str(dw_conn)
                up_interface = dic['interface']
                if up_interfaceprev != up_interface:
                    if up_interfaceprev != '0':
                        up_salida.append(dic_interface_up)
                    dic_interface_up = {}
                    dic_interface_up['cmts'] = cmts
                    dic_interface_up['up_slot'] = up_slot
                    dic_interface_up['up_conn'] = up_conn
                    dic_interface_up['up_group'] = '0'
                    dic_interface_up['dw_conn'] = dw_conn
                    dic_interface_up['mac_domain'] = mac_domain
                    f = dic['frequency'].split(' ')
                    port_up = {}
                    dic_interface_up['up_channels'] = []
                    try:
                        # Si es OFDMA
                        port_up['BW'] = int(f[1])-int(f[0])
                        port_up['freq_cen'] = int((int(f[1])+int(f[0]))/2)
                    except:
                        # Si es ATDMA
                        port_up['BW'] = dic['channel_width']
                        port_up['freq_cen'] = dic['frequency']
                    port_up['up_power'] = dic['power']
                    
                    if mod_profiles.get(dic['modulation']) == None:
                        port_up['mod'] = "undef"
                        print("caso: ")
                        print(dic)
                    else:
                        port_up['mod'] = mod_profiles[dic['modulation']].upper()
                    dic_interface_up['up_channels'].append(port_up)
                    up_interfaceprev = up_interface
                else:
                    f=dic['frequency'].split(' ')
                    port_up = {}
                    try:
                        # Si es OFDMA
                        port_up['BW'] = int(f[1])-int(f[0])
                        port_up['freq_cen'] = int((int(f[1])+int(f[0]))/2)
                    except:
                        # Si es ATDMA
                        port_up['BW'] = dic['channel_width']
                        port_up['freq_cen'] = dic['frequency']
                    port_up['up_power'] = dic['power']
                    port_up['mod'] = mod_profiles[dic['modulation']].upper()
                    dic_interface_up['up_channels'].append(port_up)
            # parseo DW
            re_tabled = textfsm.TextFSM(fd) # Levanto el template de DW
            headerd = re_tabled.header
            resultd = re_tabled.ParseText(data) # Parseo el backup con el template 'template_cbr8_dw'
            print("Parseo DW:\n", resultd)
            dw_salida = []
            dic_interface_dw = {}
            mac_domainprev = '0'        
            for lista in resultd:
                mac_domain = lista[0]
                dw_conn = lista[0].split('/')[2]
                dw_slot = lista[0].split('/')[0]
                freq = int(lista[2])
                bw = 6000000
                if mac_domainprev != mac_domain:
                    if mac_domainprev != '0':
                        dw_salida.append(dic_interface_dw)
                    dic_interface_dw = {}
                    dic_interface_dw['cmts'] = cmts
                    dic_interface_dw['dw_slot'] = dw_slot
                    dic_interface_dw['dw_conn'] = dw_conn
                    dic_interface_dw['mac_domain'] = mac_domain
                    port_dw = {}
                    dic_interface_dw['dw_channels'] = []
                    mac_domainprev = mac_domain
                #try: #Podria preguntarse si lista[3] == 'DOCSIS'
                if lista[3] == 'DOCSIS':
                    iniport = int(lista[1].split(' ')[0])
                    try:
                        finport = int(lista[1].split(' ')[1]) #En caso de OFDM aca salta a rama Except
                    except:
                        finport = iniport+2
                    port_dw['freq_cen'] = freq
                    port_dw['mod']='256QAM'
                    port_dw['BW'] = bw
                    dic_interface_dw['dw_channels'].append(port_dw)
                    for port in range(iniport+1,finport):
                        port_dw={}
                        port_dw['mod']='256QAM'
                        freq = freq + bw
                        port_dw['freq_cen'] = freq
                        port_dw['BW'] = bw
                        dic_interface_dw['dw_channels'].append(port_dw)
                #except: #Podria ser else / else if lista[3] == 'VIDEO'
                elif lista[3] == 'VIDEO':
                    #pass
                    port_dw={}
                    port_dw['mod']='CW'
                    #print(lista, "CW_AJUSTE")  #Debug Purposes
                    bw = lista[4] #Campo vacío -> hardcodear 0 ?
                    port_dw['BW'] = bw
                    freq_cen = int(lista[2])
                    port_dw['freq_cen'] = freq_cen
                    dic_interface_dw['dw_channels'].append(port_dw)
                else:
                    port_dw={}
                    port_dw['mod']='OFDM'
                    print(lista, "OFDM")  #Debug Purposes
                    bw = int(lista[4])
                    port_dw['BW'] = bw
                    freq_cen = int((freq*2+bw)/2)
                    port_dw['freq_cen'] = freq_cen
                    dic_interface_dw['dw_channels'].append(port_dw)
        salida = []
        for downstream in dw_salida:
            for upstream in up_salida:
                if downstream['mac_domain']==upstream['mac_domain']:
                    dic={}
                    dic['cmts'] = downstream['cmts']
                    dic['dw_slot'] = downstream['dw_slot']
                    dic['dw_conn'] = downstream['dw_conn']
                    dic['mac_domain'] = downstream['mac_domain']
                    dic['dw_channels'] = downstream['dw_channels']
                    dic['up_slot'] = upstream['up_slot']
                    dic['up_group'] = upstream['up_group']
                    dic['up_conn'] = upstream['up_conn']
                    dic['up_channels'] = upstream['up_channels']
                    salida.append(dic)
        output_file_url = dest_dir + cmts + '.json'
        #print("Salida:", salida)
        with open(output_file_url, 'w') as outputfile:
            json.dump(salida,outputfile)
        outputfile.close()
    else:
        print("\tNo se encontraron archivos de BackUp para", cmts)
        print("\tGenerando Excepción")
        raise Exception("No existen archivos de BackUp para "+cmts)

# Python callable Comparacion Lisy-CMTS
def Info_Compare(lisy_dir, config_dir, salida_dir, cmts):
    print("Iniciando comparacion ConfigCMTS Vs Lisy para", cmts)
    file_lisy = lisy_dir+cmts+'4db.json'
    file_config = config_dir+cmts+'.json'
    print("Verificando que existan los archivos",file_lisy,",",file_config,end=':')
    if os.path.exists(file_lisy) and os.path.exists(file_config):
        with open(file_lisy) as flisy, open(file_config) as fconfig:
            print("OK")
            data_lisy = flisy.read()
            data_config = fconfig.read()
            data_lisy = json.loads(data_lisy)
            data_config = json.loads(data_config)

            if os.path.exists(salida_dir):
                file_comp = salida_dir+cmts+".txt"
                print("Creando archivo de salida :",file_comp)
                fcomp = open(file_comp, 'w')
                fcomp.write("Resultado Compliance Lisy-CMTS: " + cmts)
            
            #seteo en 0 el contador de errores
            #(Se consulta contador para producir una falla en la task 
            # y obtener visualmente el resultado del compliance)
            errors = 0
            #Recorro las combinaciones parseadas del CMTS:
            for combinacion_config in data_config:
                #Busco contraparte en combinaciones obtenidas de Lisy:
                flag_contraparte = False
                for combinacion_lisy in data_lisy:                   
                    #Creo versiones de los diccionarios sin ch map para fácil visualizacion en la salida:
                    configDictforPrint = combinacion_config.copy()
                    configDictforPrint.pop("dw_channels")
                    configDictforPrint.pop("up_channels")
                    LisyDictforPrint = combinacion_lisy.copy()
                    if "up_channels" in LisyDictforPrint:
                        LisyDictforPrint.pop("up_channels")
                    if "dw_channels" in LisyDictforPrint:
                        LisyDictforPrint.pop("dw_channels")
                    
                    try:
                        if combinacion_lisy["mac_domain"] == combinacion_config["mac_domain"]:
                            #Chequeo si hay distinta cantidad de campos a comparar (-1 = MGT)
                            print("Comparando Config CMTS vs Info Lisy:")
                            print("\tConfig CMTS:",combinacion_config)
                            print("\t\Info Lisy:",combinacion_lisy)

                            if len(combinacion_lisy.keys())-1 !=  len(combinacion_config.keys()):
                                print("\tMenor cantidad de campos en Lisy que en CMTS")
                                camposfaltantes = combinacion_config.keys()-combinacion_lisy.keys()
                                if "dw_conn" in camposfaltantes:
                                    #Compruebo que sea el mismo FiberNode: (mismo up)
                                    if combinacion_lisy["up_conn"] == combinacion_config["up_conn"] and \
                                        combinacion_lisy["up_group"] == combinacion_config["up_group"] and \
                                        combinacion_lisy["up_slot"] == print(combinacion_lisy["up_conn"]):
                
                                        print("\t\tRegistrando discordancia en archivo de salida")
                                        fcomp.write("\n\nDiscordancia en cantidad de campos Lisy vs CMTS:\n")
                                        fcomp.write("\tCombinacion Config: (" +  str(len(combinacion_config.keys()))  +"):\n")
                                        fcomp.write(json.dumps(configDictforPrint, indent=4, sort_keys=False))
                                        fcomp.write("\n\tCombinacion Lisy (" + str(len(combinacion_lisy.keys())) +"):")
                                        fcomp.write("\n\t\tCampos ausentes en Lisy : " + str(camposfaltantes)+"\n")
                                        fcomp.write(json.dumps(LisyDictforPrint, indent=4, sort_keys=False))

                                        errors+=1
                                    else:
                                        #Son conectores de up distintos
                                        print("\t\tNO SON COMPARABLES, distinto conector de UP:")
                                else:
                                    print("\t\tRegistrando discordancia en archivo de salida")
                                    fcomp.write("\n\nDiscordancia en cantidad de campos Lisy vs CMTS:\n")
                                    fcomp.write("\tCombinacion Config: (" +  str(len(combinacion_config.keys()))  +"):\n")
                                    fcomp.write(json.dumps(configDictforPrint, indent=4, sort_keys=False))
                                    fcomp.write("\n\tCombinacion Lisy (" + str(len(combinacion_lisy.keys())) +"):")
                                    fcomp.write("\n\t\tCampos ausentes en Lisy : " + str(camposfaltantes)+"\n")
                                    fcomp.write(json.dumps(configDictforPrint, indent=4, sort_keys=False))

                            #Verifico que sea el mismo FiberNode (mismo up):
                            elif combinacion_lisy["up_conn"] == combinacion_config["up_conn"] :# and \
                                #combinacion_lisy["up_group"] == combinacion_config["up_group"] and \
                                #combinacion_lisy["up_slot"] == print(combinacion_lisy["up_conn"]):
                                
                                flag_contraparte = True

                                #Verificar si tiene sentido la siguiente comprobacion, si no borrar bloque
                                if combinacion_lisy["dw_conn"] != combinacion_config["dw_conn"]:
                                    fcomp.write("\n\nDiscordancia en campo [dw_conn]  para DW: " + str(combinacion_config["mac_domain"]) + " - UP: " + \
                                    str(combinacion_config["up_slot"]) + "/" + str(combinacion_config["up_group"]) + "/" + str(combinacion_config["up_conn"]) + \
                                    "- MGT: " + str(combinacion_lisy["mgt"]))
                                    fcomp.write("\n\tInfo Lisy: " + str(combinacion_lisy["dw_conn"]))
                                    fcomp.write("\n\tInfo CMTS: " + str(combinacion_config["dw_conn"]))
                                    errors+=1
                                ######################################################################

                                ####################################################
                                #               Comparacion de CHMAPS
                                ####################################################
                                ###                       UP                     ###
                                print("\tComparando Upstream Channel Maps...") 
                                #Ordeno chmaps para comparar:
                                chMapLisy=sorted(combinacion_lisy["up_channels"], key = lambda kv: int(kv["freq_cen"]))
                                chMapConfig=sorted(combinacion_config["up_channels"], key = lambda kv: int(kv["freq_cen"]))

                                for i in range(len(chMapConfig)):
                                    if int(chMapLisy[i]['freq_cen']) != int(chMapConfig[i]['freq_cen']):
                                        print("\t\tSe encontraron diferencias en frecuencias de portadoras")
                                        print("\t\tRegistrando errores en archivo de salida")
                                        fcomp.write("\n\nDiferencia en UP CH Maps!\n")
                                        fcomp.write("Combinacion:\n")
                                        fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False))
                                        fcomp.write("\nFrecs CMTS:\t\tFrecs Lisy:\n")
                                        for i in range(len(chMapConfig)):
                                            fcomp.write(str(chMapConfig[i]['freq_cen'])+"\t\t"+str(chMapLisy[i]['freq_cen'])+"\n")
                                        errors+=1
                                        break
                                    elif chMapLisy[i]['mod'] != chMapConfig[i]['mod']:
                                        print("\t\tSe encontraron diferencias en modulacion de portadoras")
                                        print("\t\tRegistrando errores en archivo de salida")
                                        fcomp.write("\n\nDiferencia en UP CH Maps! - Campo: Modulacion\n")
                                        fcomp.write("Combinacion:\n")
                                        fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en CMTS:\n")
                                        fcomp.write(json.dumps(chMapConfig[i],indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en Lisy:\n")
                                        fcomp.write(json.dumps(chMapLisy[i],indent=4,sort_keys=False)+"\n")
                                        errors+=1
                                    elif int(chMapLisy[i]['BW']) != int(chMapConfig[i]['BW']):
                                        print("\t\tSe encontraron diferencias en BW de portadoras")
                                        print("\t\tRegistrando errores en archivo de salida")
                                        fcomp.write("\n\nDiferencia en UP CH Maps! - Campo: BW\n")
                                        fcomp.write("Combinacion:\n")
                                        fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en CMTS:\n")
                                        fcomp.write(json.dumps(chMapConfig[i],indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en Lisy:\n")
                                        fcomp.write(json.dumps(chMapLisy[i],indent=4,sort_keys=False)+"\n")
                                        errors+=1
                                    elif int(chMapLisy[i]['up_power']) != int(chMapConfig[i]['up_power']):
                                        print("\t\tSe encontraron diferencias en UP de portadoras")
                                        print("\t\tRegistrando errores en archivo de salida")
                                        fcomp.write("\n\nDiferencia en UP CH Maps! - Campo: up_power\n")
                                        fcomp.write("Combinacion:\n")
                                        fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en CMTS:\n")
                                        fcomp.write(json.dumps(chMapConfig[i],indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en Lisy:\n")
                                        fcomp.write(json.dumps(chMapLisy[i],indent=4,sort_keys=False)+"\n")
                                        errors+=1                                    
                                    else:
                                        print("\t\tCoincide Info Portadora UP CMTS vs Lisy!")

                                ###                       DW                     ###
                                print("\tComparando Downstream Channel Maps...") 
                                #Ordeno chmaps para comparar:
                                chMapLisy=sorted(combinacion_lisy["dw_channels"], key = lambda kv: int(kv["freq_cen"]))
                                chMapConfig=sorted(combinacion_config["dw_channels"], key = lambda kv: int(kv["freq_cen"]))

                                for i in range(len(chMapConfig)):
                                    if int(chMapLisy[i]['freq_cen']) != int(chMapConfig[i]['freq_cen']):
                                        print("\t\tSe encontraron diferencias en frecuencias de portadoras")
                                        print("\t\tRegistrando errores en archivo de salida")
                                        fcomp.write("\n\nDiferencia en DW CH Maps!\n")
                                        fcomp.write("Combinacion:\n")
                                        fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False))
                                        fcomp.write("\nFrecs CMTS:\t\tFrecs Lisy:\n")
                                        for i in range(len(chMapConfig)):
                                            fcomp.write(str(chMapConfig[i]['freq_cen'])+"\t\t"+str(chMapLisy[i]['freq_cen'])+"\n")
                                        errors+=1
                                        break
                                    elif chMapLisy[i]['mod'] != chMapConfig[i]['mod']:
                                        print("\t\tSe encontraron diferencias en modulacion de portadoras")
                                        print("\t\tRegistrando errores en archivo de salida")
                                        fcomp.write("\n\nDiferencia en DW CH Maps! - Campo: Modulacion\n")
                                        fcomp.write("Combinacion:\n")
                                        fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en CMTS:\n")
                                        fcomp.write(json.dumps(chMapConfig[i],indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en Lisy:\n")
                                        fcomp.write(json.dumps(chMapLisy[i],indent=4,sort_keys=False)+"\n")
                                        errors+=1
                                    elif int(chMapLisy[i]['BW']) != int(chMapConfig[i]['BW']):
                                        print("\t\tSe encontraron diferencias en BW de portadoras")
                                        print("\t\tRegistrando errores en archivo de salida")
                                        fcomp.write("\n\nDiferencia en DW CH Maps! - Campo: BW\n")
                                        fcomp.write("Combinacion:\n")
                                        fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en CMTS:\n")
                                        fcomp.write(json.dumps(chMapConfig[i],indent=4,sort_keys=False)+"\n")
                                        fcomp.write("Config portadora en Lisy:\n")
                                        fcomp.write(json.dumps(chMapLisy[i],indent=4,sort_keys=False)+"\n")
                                        errors+=1
                                    else:
                                        print("\t\tCoincide info portadora DW CMTS vs Lisy")
                            else:
                                print("\tNo son comparables (distinto FiberNode)")
                    except Exception as e:
                        print(e)

                #Si no hubo contraparte en Lisy:        
                if not flag_contraparte: 
                    """fcomp.write("\n\nPuerto configurado en CMTS, No activo en Lisy: MAC DOMAIN: " +str(combinacion_config["mac_domain"]) + " - UP: " + \
                                str(combinacion_config["up_slot"]) + "/" + str(combinacion_config["up_group"]) + "/" + str(combinacion_config["up_conn"]) + \
                                " - DW: " + str(combinacion_config["dw_slot"]) + "/" + str(combinacion_config["dw_conn"]))
                    """
                    print("\tNo se encontró info de la combinacion en Lisy")
                    print("\tRegistrando en archivo de salida")
                    fcomp.write("\n\nPuerto configurado en CMTS, No activo en Lisy:\n")
                    fcomp.write(json.dumps(configDictforPrint,indent=4,sort_keys=False))
                    errors+=1
            #Verifico en otro sentido (Existe en Lisy y no en CMTS:)
            print("Verificando si existe Info en Lisy que no se encuentre en el CMTS...")
            for combinacion_lisy in data_lisy:
                flag_contraparte = False
                for combinacion_config in data_config:
                    if combinacion_lisy["mac_domain"] == combinacion_config["mac_domain"]:
                            flag_contraparte = True
                if not flag_contraparte:
                    print("\tPuerto Activo en Lisy, No configurado en CMTS:", combinacion_lisy)
                    fcomp.write("\nPuerto Activo en Lisy, No configurado en CMTS: ")
                    fcomp.write((json.dumps(LisyDictforPrint, indent=4, sort_keys=False)))
                    errors+=1
            #fcomp.write("Se registraron ", errors, "errores")
            fcomp.close()
            if errors > 0:
                print("#####################################################################")
                print("\tSe finalizó comparación para",cmts)
                print("\tSe registraron",errors,"errores: ", end=" ")
                print("\tGenerando Excepcion para notificar en resultado de task")
                print("#####################################################################")
                raise Exception("Se registraron " + str(errors) + " errores")
            else:
                print("#####################################################################")
                print("\tSe finalizó comparación para",cmts)
                print("\tFelicitaciones! No se registraron errores, CMTS en compliance!")
                print("#####################################################################")
    else:
        if not os.path.exists(file_lisy):
            raise Exception("No existe el archivo "+file_lisy)
        elif not os.path.exists(file_config):
            raise Exception("No existe el archivo "+file_config)

# Lectura DB inventario
def read_mongo(modelo=None):
    #HOST y PORT no cambia ya que es la mongo de TAMBO
    HOST = 'tambo_mongodb'
    PORT = 27017
    mCli = pymongo.MongoClient(HOST,PORT)
    #SETEO la DB a USAR : formio
    mDb = mCli["formio"]
    #SETEO la colección: forms
    mColForm = mDb["hostname"]

    result = [] 
    try:
        #Filtro el documento dentro de la coleción que tiene la key "title" con valor "inventario_cmts"
        for equipos in mColForm.find({'ShelfNetworkRole':"HFC ACCESS", 'Modelo':modelo}):
            result.append(equipos['ShelfName'])
    except:
        result = ["Formulario sin registros"]
    print(result)
    return result

# Tasks
def group(cmts, **kwargs):
    t1 = LisyQueryCustom(
        task_id='LisyQueryCombinaciones-{}'.format(cmts), 
        query_id = 'OcupacionRedHFC-VistaFisica',
        my_filter = '["","{}",""]'.format(cmts),
        dest_dir = '/io/cel_afijo/tmp/CompliancePuertosLisy/',
        file_name = '{}'.format(cmts),
        dag=dag
    )
    #t1 = DummyOperator(task_id='LisyQueryDummy'+cmts, retries=1, dag=dag)

    t2 = PythonOperator(
    task_id='GeneraJson4Mongo'+cmts,
    python_callable=ExtraeInfo,
    op_kwargs={'dest_dir':'/io/cel_afijo/tmp/CompliancePuertosLisy/', 'file_name':cmts, 'shutdown':True},
    provide_context = False,
    dag=dag
    )

    #t2 = DummyOperator(task_id='GeneraJsonLisyDummy'+cmts, retries=1, dag=dag)

    t3 = PythonOperator(
    task_id = "ParseoConfig_"+cmts,
    python_callable = Select_Parser,
    op_kwargs = {'dest_dir':'/io/cel_afijo/tmp/CompliancePuertosConfig/', 'cmts':cmts},
    provide_context = False,
    dag=dag
    )
    #t3 = DummyOperator(task_id='ParseoConfigDummy'+cmts, retries=1, dag=dag)

    t4 = PythonOperator(
    task_id = "Comparacion_"+cmts,
    python_callable = Info_Compare,
    op_kwargs = {'lisy_dir':'/io/cel_afijo/tmp/CompliancePuertosLisy/', 'config_dir':'/io/cel_afijo/tmp/CompliancePuertosConfig/','salida_dir':'/io/cel_afijo/per/CompliancePuertosCMTS_Lisy/', 'cmts':cmts},
    provide_context = False,
    retries=0,
    dag=dag
    )

    return t0 >> t1 >> t2 >> t3 >> t4

t0 = DummyOperator(task_id='INICIO', retries=1, dag=dag)

modelo='CBR8'
equipos = read_mongo(modelo)
#modelo='C100G'
#equipos2 = read_mongo(modelo)
#equipos += equipos2
#modelo='E6K'
#equipos3 = read_mongo(modelo)
#equipos += equipos3

equipos = ['CMT1.CON1-C100G','CMT2.RCU1-CBR8', 'CMT1.JMA1-C100G', 'CMT5.DEV1-E6K']
#equipos = ['CMT2.RCU1-CBR8']
for i in equipos:
    group(i)