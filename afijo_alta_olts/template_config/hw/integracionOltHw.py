import sys
import textfsm


def create_template_olt_hw(puerto1Olt:str=None,puerto2Olt:str=None,ipToipOlt:str=None,maskToipBin:str=None,collection_of_alarms:list=[],collection_of_boards:list=[],sections:list=[]):
    """
    section:list -> parametro no obligatorio, si se espesifica una o varias secciones a configurar el resultado del diccionario solo contendrá esas secciones
        
        # puerto1Olt= "0/9"
        # puerto2Olt= "0/10"
        # ipToipOlt= "10.248.0.2"
        # maskToipBin= "255.255.224.0"
    """

    #### Ejemplo de Parseo y generacion de comandos para los undo trap filter ########
    lista_placas_soportadas = ['H902FLHF','H807GPBH','H901GPHF','H802GPBD','H902GPHF','H902FLHF','H903GPHF','H903FLHF']



    commands_tacast  =   [
                "enable",
                "config",
                "undo smart",
                "aaa",
                "authentication-scheme tacacs-group",
                "authentication-mode hwtacacs",
                "quit",
                "authorization-scheme tacacs-group",
                "authorization-mode hwtacacs",
                "quit",
                "accounting-scheme tacacs-group",
                "accounting-mode hwtacacs",
                "quit",
                "quit",
                "hwtacacs-server template hwtest",
                "hwtacacs-server shared-key argentina2001",
                "hwtacacs-server authentication 200.43.9.251",
                "hwtacacs-server authentication 200.43.9.15 secondary",
                "hwtacacs-server authorization 200.43.9.251",
                "hwtacacs-server authorization 200.43.9.15 secondary",
                "hwtacacs-server accounting 200.43.9.251",
                "hwtacacs-server accounting 200.43.9.15 secondary",
                "quit",
                "aaa",
                "domain teco",
                "authentication-scheme tacacs-group",
                "authorization-scheme tacacs-group",
                "accounting-scheme tacacs-group",
                "hwtacacs-server hwtest",
                "quit",
                "quit",          
                ]
    commands_circuit    =   [
                "enable",
                "config",
                "undo smart",
                "alarm output all",
                "event output all",
                "raio-format pitp-pmode rid xpon splabel",
                "raio-format dhcp-option82 cid xpon anid xpon frame/slot/subslot/port:vlanid.ontid.sn",
                "raio-format dhcp-option82 rid xpon anid",
                "raio-format dhcpv6-option rid xpon splabel",
                "raio-format pitp-pmode cid xpon anid xpon frame/slot/subslot/port:vlanid.ontid.sn",
                "raio-mode user-defined pitp-pmode",
                "pitp enable pmode",
                "raio-mode user-defined dhcp-option82"
                            ]
    commands_dhcp   =   [
                "enable",
                "config",
                "undo smart",
                {"dhcp option82 enable":[{'prompt':'Are you sure to perform this operation? (y/n)[n]:'},{'answer':'y'}]},#Are you sure to perform this operation? (y/n)[n]:
                {"dhcp mode layer-2":[{'prompt' : 'Are you sure to perform this operation? (y/n)[n]:'},{'answer' : 'y'}]}#Are you sure to perform this operation? (y/n)[n]:
                       ] 
    commands_net    =   [   
                "enable",
                "config",
                "undo smart",
                {"vlan 6 to 7 smart": [{'prompt':'Are you sure to add VLANs? (y/n)[n]:'},{'answer':'y'}]},#Are you sure to add VLANs? (y/n)[n]:
                {"vlan 29 to 30 smart": [{'prompt':'Are you sure to add VLANs? (y/n)[n]:'},{'answer':'y'}]},#Are you sure to add VLANs? (y/n)[n]:
                {f"port vlan 29 to 30 {puerto1Olt} 0": [{'prompt':'Are you sure to add standard port(s)? (y/n)[n]:'},{'answer':'y'}]},#Are you sure to add standard port(s)? (y/n)[n]:
                "quit"
                    ] 
    commands_vlan_29    =   [
                "enable",
                "config",
                "undo smart",       
                "interface Vlanif29",
                f"ip address {ipToipOlt} {maskToipBin}",            
                "quit"
                        ]
    commands_btv    =   [ 
                "enable",
                "config",
                "undo smart",
                "multicast-vlan 6"
                    ]
    commands_snmp    =   [
                "enable",
                "config",
                "undo smart",
                "snmp-agent community read public.Teco2021",
                "snmp-agent community write private.Teco2021",
                "snmp-agent sys-info version v1 v2c v3",
                "snmp-agent sys-info contact IMP_XDSL@teco.com.ar",
                "snmp-agent sys-info location Argentina",
                "snmp-agent trap enable standard",
                "snmp-agent target-host trap-hostname NCE_HOR address 172.18.4.29 udp-port 162 trap-paramsname Telecom",
                "snmp-agent target-host trap-hostname NCE_SLO address 172.18.4.50 udp-port 162 trap-paramsname Telecom",
                "snmp-agent target-host trap-paramsname Telecom v1 securityname private.Teco2021"
                ]
    commands_loghost    =   [
                "enable",
                "config",
                "undo smart",
                "syslog enable alarm-event",
                "loghost add 172.18.4.29 NCE_HOR",
                "loghost activate ip 172.18.4.29",
                "loghost add 172.18.4.50 NCE_SLO",
                "loghost activate ip 172.18.4.50",
                "loghost add 190.227.215.10 Servidor_Scannet2",
                "loghost activate ip 190.227.215.10",
                "loghost add 190.227.215.18 Servidor_Scannet1",
                "loghost activate ip 190.227.215.18"]  
    commands_ACL_4020   =   [
                "enable",
                "config",
                "undo smart",  
                "acl 4020",
                "description OPEN v2",
                "rule 10 permit cos 1 source 30", 
                "rule 15 permit cos 2 source 30",
                "rule 20 permit cos 3 source 30"
                            ]
    commands_ACL_4021   = [   
                "enable",
                "config",
                "undo smart",   
                "acl 4021",
                "description OPEN v2",
                "rule 10 permit cos 4 source 30", 
                "rule 15 permit cos 5 source 30",
                "rule 20 permit cos 6 source 30",
                "rule 25 permit cos 7 source 30"
                      ]  
    commands_ACL_to_port  =   [
                "enable",
                "config",
                "undo smart",
                f"traffic-priority inbound link-group 4020 cos 0 port {puerto1Olt}/0",
                f"traffic-priority inbound link-group 4020 cos 0 port {puerto2Olt}/0",
                f"traffic-priority inbound link-group 4021 cos 2 port {puerto1Olt}/0",
                f"traffic-priority inbound link-group 4021 cos 2 port {puerto2Olt}/0"
                        ]        
    commands_ntp  =   [
                "enable",
                "config",
                "undo smart",
                "ntp-service server disable",
                "ntp-service unicast-server 172.18.4.29"]
    commands_alarm = [
                      "enable",
                      "config",
                      "undo smart"]
    commands_confim_board = [
                            "enable",
                            "config",
                            "undo smart"]
    commands_autofind = [
                            "enable",
                            "config",
                            "undo smart"]

    for item in collection_of_boards:
        if item.get('modelo') in lista_placas_soportadas and item.get('estado') == 'Auto_find':
            commands_confim_board.append(f"board confirm 0/{item.get('board')}")

    for item in collection_of_boards:
        if item.get('modelo') in lista_placas_soportadas and item.get('estado') != 'Failed':
            commands_autofind.append(f"interface gpon 0/{item.get('board')}")
            [commands_autofind.append(f'port {x} ont-auto-find enable') for x in range(16)]           

    for item in collection_of_alarms:
        commands_alarm.append(f"undo trap filter {item.get('evento')} condition id {item.get('id')}")
        



    if len(sections)>0:
        set_de_comandos_alta = {}
        for seccion in sections:
            if seccion == "commands_confim_board":
                set_de_comandos_alta[seccion] = commands_confim_board 
            if seccion == "commands_tacast":
                set_de_comandos_alta[seccion] = commands_tacast 
            if seccion == "commands_circuit":
                set_de_comandos_alta[seccion] = commands_circuit 
            if seccion == "commands_dhcp":
                set_de_comandos_alta[seccion] = commands_dhcp 
            if seccion == "commands_net":
                set_de_comandos_alta[seccion] = commands_net 
            if seccion == "commands_vlan_29":
                set_de_comandos_alta[seccion] = commands_vlan_29 
            if seccion == "commands_btv":
                set_de_comandos_alta[seccion] = commands_btv 
            if seccion == "commands_snmp":
                set_de_comandos_alta[seccion] = commands_snmp 
            if seccion == "commands_loghost":
                set_de_comandos_alta[seccion] = commands_loghost 
            if seccion == "commands_ACL_4020":
                set_de_comandos_alta[seccion] = commands_ACL_4020 
            if seccion == "commands_ACL_4021":
                set_de_comandos_alta[seccion] = commands_ACL_4021 
            if seccion == "commands_ACL_to_port":
                set_de_comandos_alta[seccion] = commands_ACL_to_port 
            if seccion == "commands_ntp":
                set_de_comandos_alta[seccion] = commands_ntp 
            if seccion == "commands_alarm":
                set_de_comandos_alta[seccion] = commands_alarm 
            if seccion == "commands_autofind":
                set_de_comandos_alta[seccion] = commands_autofind 
            if seccion == "users":
                # set_de_comandos_alta[seccion] = users 
                pass
    else:
        set_de_comandos_alta = {
            "commands_confim_board" : commands_confim_board,
            "commands_tacast":commands_tacast,
            "commands_circuit": commands_circuit,
            "commands_dhcp":commands_dhcp,
            "commands_net":commands_net,
            "commands_vlan_29":commands_vlan_29,
            "commands_btv":commands_btv,
            "commands_snmp": commands_snmp, #SNMP ACTUAL R20,
            "commands_loghost":commands_loghost,
            "commands_ACL_4020":commands_ACL_4020,
            "commands_ACL_4021":commands_ACL_4021,
            "commands_ACL_to_port":commands_ACL_to_port,
            "commands_ntp":commands_ntp,
            "commands_alarm":commands_alarm,
            "commands_autofind":commands_autofind,
            # "users":users
            }
    
    return set_de_comandos_alta


def parser_command(path_fsm:str=None, text_to_parse:str = None):
    collection_of_results = []      #### ---> Lista con el resultado del parseo
    print("Path->")
    print(path_fsm)
    print("Data->")
    print(text_to_parse)
    with open(path_fsm) as f:
        re_table = textfsm.TextFSM(f)
        header = re_table.header
        result = re_table.ParseText(text_to_parse)
        collection_of_results = [dict(zip(header, pr)) for pr in result]
    return collection_of_results