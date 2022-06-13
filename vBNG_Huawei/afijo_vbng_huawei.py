import os
import sys
import xml.dom.minidom
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from ncclient import manager
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
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'provide_context': True,
    'dag_type': 'custom'
}
        
###################### def del dag ##########################
dag = DAG(
    dag_id= DAG_ID, 
    schedule_interval= None, 
    default_args=default_args
)

#######################def script python PPP ###################

def Interface_CP_PPP_NETCONF(**kwargs):
    # netconfSession = manager.connect(
    # host = "IP", # IP DEL HOST A CONFIGURAR
    # port = 830, # PUERTO NETCONF, DEFAULT 830
    # username = "USUARIO",
    # password = "PASSWORD",
    # hostkey_verify = False,
    # device_params = {'name': 'huaweiyang'} # MODELO DE PARAMETRO DE DATOS
    # )
    
    log = {}
    log = TAMBO.GetForms(DAG_ID)
     
    rpcMessage = '''<config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <ifm xmlns="urn:huawei:yang:huawei-ifm">   Archivo YANG dentro del equipo
    <interfaces>
        <interface>
        <name>GigabitEthernet{0}.30</name>  VARIABLE
        <class>sub-interface</class>
        <type>GigabitEthernet</type>
        <parent-name>GigabitEthernet{0}</parent-name>
        <number>30</number>
        <description>[DATOS] {1} {2} {3} [GPON]</description>
        <ethernet xmlns="urn:huawei:yang:huawei-ethernet">
            <l3-sub-interface>
            <user-vlan-common>
                <user-vlan-dot1q>
                <vlan-list>30</vlan-list>
                </user-vlan-dot1q>
            </user-vlan-common>
            </l3-sub-interface>
        </ethernet>
        <bas xmlns="urn:huawei:yang:huawei-bras-basic-access">
            <layer2-subscriber>
            <subscriber-base>
                <default-domain-type>force</default-domain-type>
                <default-domain-name>test</default-domain-name>
            </subscriber-base>
            <nas-port-type>
                <type>x.25</type>
            </nas-port-type>
            <nas-logic>
                <ip-address>{4}</ip-address>
            </nas-logic>
        </bas>
        <pppoe-bind-vt xmlns="urn:huawei:yang:huawei-bras-pppox-access"> 
            <name>Virtual-Template1</name>
        </pppoe-bind-vt>
        </interface>
    </interfaces>
    </ifm>
    </config>'''.format(log['NdeInterfaz'],log['NombreOlt'],log['vendor'],log['modelo'], log['IPCX'])

    print(rpcMessage)
#    response = netconfSession.edit_config(target = 'candidate', config = rpcMessage)
#    netconfSession.commit()
#    netconfSession.close_session()
#    print(response.xml)


#######################def script python Gestión ###################

def Interface_UP_GESTION_NETCONF(**kwargs):
    log = {}
    log = TAMBO.GetForms(DAG_ID)
     
    rpcMessage = '''<config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <ifm xmlns="urn:huawei:yang:huawei-ifm"> 
    <interfaces>
        <interface>
        <name>GigabitEthernet{0}.2101</name>
        <class>sub-interface</class>
        <type>GigabitEthernet</type>
        <parent-name>GigabitEthernet{0}</parent-name>
        <number>2101</number>
        <description>{1} {2} {3}</description>
        <vrf-name>{4}</vrf-name>
        <l2-mode-enable>false</l2-mode-enable>
        <ethernet xmlns="urn:huawei:yang:huawei-ethernet">
          <l3-sub-interface>
            <vlan-type-dot1q>
              <vlan-type-vid>21</vlan-type-vid> 
            </vlan-type-dot1q>
          </l3-sub-interface>
        </ethernet>
        <ipv4 xmlns="urn:huawei:yang:huawei-ip">
          <addresses>
            <address>
              <ip>{5}</ip> 
              <mask>{6}</mask> 
              <type>main</type>
            </address>
          </addresses>
        </ipv4>
        </interface>
    </interfaces>
    </ifm>
    </config>'''.format(log['Interfazcx'],log['NombreOlt'],log['vendor'],log['modelo'],log['vrf'],log['ipgestion'],log['gestionmascara'])

    print(rpcMessage)
    return log

#######################def script python TOIP ###################

def Interface_UP_TOIP_NETCONF(**kwargs):
    log = {}
    log = TAMBO.GetForms(DAG_ID)

    rpcMessage = '''<config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <ifm xmlns="urn:huawei:yang:huawei-ifm"> 
    <interfaces>
        <interface>
        <name>GigabitEthernet{0}.3101</name>
        <class>sub-interface</class>
        <type>GigabitEthernet</type>
        <parent-name>GigabitEthernet{0}</parent-name>
        <number>3101</number>
        <description>{1} {2} {3}</description>
        <vrf-name>vpn-a</vrf-name>
        <l2-mode-enable>false</l2-mode-enable>
        <ethernet xmlns="urn:huawei:yang:huawei-ethernet">
            <l3-sub-interface>
            <vlan-type-dot1q>
                <vlan-type-vid>31</vlan-type-vid>
            </vlan-type-dot1q>
            </l3-sub-interface>
        </ethernet>
        <ipv4 xmlns="urn:huawei:yang:huawei-ip">
            <addresses>
            <address>
                <ip>{4}</ip>
                <mask>{5}</mask>
                <type>main</type>
            </addresses>
        </ipv4>
        <dhcp-relay-attribute xmlns="urn:huawei:yang:huawei-dhcp">
            <enable>true</enable>
            <server-addresses>
            <server-address>
                <address>{6}</address>
            </server-address>
            <server-address>
                <address>{7}</address>
            </server-address>
            </server-addresses>
        </dhcp-relay-attribute>
        <dhcp-relay-if xmlns="urn:huawei:yang:huawei-dhcp">
            <is-enable>true</is-enable>
            <server-addresses>
            <server-address>
                <address>{6}</address>
            </server-address>
            <server-address>
                <address>{7}</address>
            </server-address>
            </server-addresses>
        </dhcp-relay-if>
        </interface>
    </interfaces>
    </ifm>
    </config> '''.format(log['Interfaztoip'],log['NombreOlt'],log['vendor'],log['modelo'],log['ipgateway'],log['maskgateway'],log['Ipdchpp'],log['Ipdhcps'])

    print(rpcMessage)
    return log
    

#def Interface_UP_GESTION_NETCONF(**kwargs):
# DECLARACION DE LA INSTANCIA DE manager.connect
#    netconfSession = manager.connect(
#    host = "IP", # IP DEL HOST A CONFIGURAR
#    port = 830, # PUERTO NETCONF, DEFAULT 830
#    username = "USUARIO",
#    password = "PASSWORD",
#    hostkey_verify = False,
#    device_params = {'name': 'huaweiyang'} # MODELO DE PARAMETRO DE DATOS
#    )
#    rpcMessage = '''<config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
#  <ifm xmlns="urn:huawei:yang:huawei-ifm">
#    <interfaces>
#      <interface>
#        <name>GigabitEthernet0/6/0.2101</name>
#        <class>sub-interface</class>
#        <type>GigabitEthernet</type>
#        <parent-name>GigabitEthernet0/6/0</parent-name>
#        <number>2101</number> VARIABLE SUBINTERFACE
#        <description>PRUEBA NETCONF GESTION/MANAGEMENT</description> 
#        <vrf-name>vpn-a</vrf-name> 
#        <l2-mode-enable>false</l2-mode-enable> 
#        <ethernet xmlns="urn:huawei:yang:huawei-ethernet"> 
#          <l3-sub-interface>
#            <vlan-type-dot1q>
#              <vlan-type-vid>21</vlan-type-vid> 
#            </vlan-type-dot1q>
#          </l3-sub-interface>
#        </ethernet>
#        <ipv4 xmlns="urn:huawei:yang:huawei-ip">  Archivo YANG dentro del equipo
#          <addresses>
#            <address>
#              <ip>192.168.0.10</ip>  VARIABLE IP GESTIÓN
#              <mask>255.255.255.0</mask>  VARIABLE MASCARA
#              <type>main</type> Dato por default
#            </address>
#          </addresses>
#        </ipv4>
#      </interface>
#    </interfaces>
#  </ifm>
# </config>'''
#    response = netconfSession.edit_config(target = 'candidate', config = rpcMessage)
#    netconfSession.commit()
#    netconfSession.close_session()
#    print(response.xml)


####################### def de task #########################
task_0 = DummyOperator(task_id='INICIO', retries=1, dag=dag)

#task_2 = DummyOperator(task_id='tarea_02_dummy', retries=1, dag=dag)

task_1 = PythonOperator(
    task_id='Interface_CP_PPP_NETCONF',
    python_callable=Interface_CP_PPP_NETCONF,
    dag=dag
    )

task_2 = PythonOperator(
    task_id='Interface_UP_TOIP_NETCONF',
    python_callable=Interface_UP_TOIP_NETCONF,
    dag=dag
    )

task_3 = PythonOperator(
    task_id='Interface_UP_GESTION_NETCONF',
    python_callable=Interface_UP_GESTION_NETCONF,
    dag=dag
    )

#task_4 = PythonOperator(
#    task_id='Get_Data_Formulario',
#    python_callable=formio,
#    dag=dag
#    )


##########################ejecucion de task #################

task_0 >> task_1 
task_0 >> task_2 >> task_3
# task_0 >> task_4 
 
 
 
 
 
 
 
 
 
 
 
 



