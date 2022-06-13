"""
    Documentar codigo con Docstring
    Path de este directorio /usr/local/airflow/dags/cel_core
    Path de la carpeta Ansible /urs/local/ansible/
"""

# import defaults
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import pymongo

#import propios
from lib.core_tcg_clases import *
#from f_teco_flatten import *
from lib.teco_json_c_list import *
from lib.core_tcg_funciones_embebidas import *
from lib.teco_events import *
from lib.L_teco_db import *

# import adicionales
import re
import math
import difflib
from jinja2 import Template
import json
import glob

DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'core',
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
    dag_id= 'afijo_TCGComplianceIntegrado', 
    schedule_interval= None, 
    default_args=default_args
)

# Funciones cutomizadas del DAG

# def f_limpio_archivos(**context):
#     element=context['NODO']
#     owner=context['OWNER']
#     wdir=context['WORK_DIR']+"/"+str(owner)+"/"+str(element)

#     try:
#         os.remove(wdir+"/"+str(owner)+"_"+str(element)+"_config_full.cfg")
#         os.remove(wdir+"/"+str(owner)+"_"+str(element)+"_config_validada.cfg")
#         os.remove(wdir+"/"+str(owner)+"_"+str(element)+"_config_solved.cfg")
#         os.remove(wdir+"/"+str(owner)+"_"+str(element)+"_template_solved.tcg")                
#     except:
#         pass

def exec_directiva(directiva,lineax_tcg,config,owner,element,debug):
    cumple = False
    for linea_cfg in config.lineas_cfg:  #<------------------------!!! podria matchear linea tcg directamente a toda la config, en vez de for y match independiente por linea config
                                            # en realidad voy a necesitar barrer por linea de config porque tengo que marcarla como valida o no, pero fijate de hacerlo todo en misma recorrida!!!!
        m=re.match("^"+lineax_tcg.patron+"$",linea_cfg.texto)


        if m:
            cumple=True
            if debug > 2:
                print("exec_directiva - Hay al menos un MATCH dentro de Configuracion")
            #break


            if cumple and directiva == "N":
                if debug > 1:
                    print("exec_directiva - MATCH y es Negada asique: le pongo estado=negada (en todas las lineas de config que coinciden) y marco la linea TCG como mandatory_failed")

                linea_cfg.estado="negada"
                ##print("Mandatory_failed - negate")
                lineax_tcg.mandatory_failed = True
                if lineax_tcg.trap != "":
                                    facility = "COMPLIANCE"
                                    message = "Mandatorio no cumplido :"+str(lineax_tcg.texto)
                                    severity = lineax_tcg.trap.replace("TRAP_","")
                                    send_tambo_event(OWNER=owner,ELEMENT=element,FACILITY=facility,SEVERITY=severity,MESSAGE=message)
                                    #print("ENVIO SYSLOG:"+str(facility) + "-" + str(severity) + "-" + str(message))	
                                    if debug > 1:
                                        print("Send SYSLOG: "+str(message))
                ############## no hago break porque misma linea tcg podria validar mas de una linea de config!!!!!!!!!!!!!!!!!!podrias usar directiva unique o ver si no tiene regexpy ahi hacer break
                if lineax_tcg.literal:
                    break  #si es literal no sigo barriendo config, porque solo puede matchear con una linea en config y ya la procese aca
            #matcheo ok y no es Pass		
            elif cumple and directiva != "P":

                if debug > 1:
                    print("exec_directiva - MATCH, No Es Negada y no es PASS -> validada y veo si warning en TODAS las lineas de config")

                ##print("validada")
                #negada tiene prioridad sobre validada, si una misma linea de config es marcada como negada y como validada debe quedar negada

                if linea_cfg.estado!="negada":
                    linea_cfg.estado="validada"
                # Me fijo si tiene warning
                if lineax_tcg.warning:
                    linea_cfg.warning=True
                if lineax_tcg.literal:
                    break
            #matcheo ok y es pass
            elif cumple and directiva == "P":

                if debug > 1:
                    print("exec_directiva - MATCH, No Es Negada y ES PASS -> marco todas las lineas de config como PASS")


                if m:
                    linea_cfg.estado="negada"
                    ##print("puesta como pass")
                    linea_cfg.d_pass=True

                    if lineax_tcg.warning:
                        linea_cfg.warning=True

                if lineax_tcg.literal:
                    break
            else:
                print("ERROR - Condicion no contemplada : "+str(lineax_tcg.texto))

    if not cumple:
                
        # TCG no matchea con ninguna linea de config y NO es optativa
        if not lineax_tcg.optative:

                if debug > 1:
                    print("exec_directiva - NO MATCH y MAndatoria -> marco mandatory_failed en linea tcg y mando syslog")

                ##print("Mandatory_failed1")
                lineax_tcg.mandatory_failed = True
                if lineax_tcg.trap != "":
                            facility = "COMPLIANCE"
                            message = "Mandatorio no cumplido :"+str(lineax_tcg.texto)
                            severity = lineax_tcg.trap.replace("TRAP_","")
                            send_tambo_event(OWNER=owner,ELEMENT=element,FACILITY=facility,SEVERITY=severity,MESSAGE=message)
                            #print("ENVIO SYSLOG:"+str(facility) + "-" + str(severity) + "-" + str(message))

                            if debug > 1:
                                print("Send SYSLOG: "+str(message))

    if debug > 1:
            print("-----  FIN exec_directiva  -------------------------------------------")



def f_Compliance_Unificado(**context):


    file_tcg=context['file_tcg']
    config_file=context['config_file']
    owner=context['OWNER']
    try:
        element=config_file.split(".config")[0]  ###### el archivo de configuracion debe tener extension .config
        element=element.split("_")[-1]   ####  y antes del punto debe estar el nombre den nodo
    except:
        element = "unknown"


    
    try:
        debug = context['DEBUG_LEVEL']
    except:
        debug = 2  #Nivel de debugging default (0,1,2)


    archivo_cfg = str(config_file)+".flatten"
    archivo_tcg = str(file_tcg)+".solved"
    arch_config_validada = str(config_file)+".validada"
    arch_config_no_validada = str(config_file)+".no_validada"
    arch_config = str(config_file)+".full"  # con mandatorios para hacer el diff

    filename = arch_config+".diff.html"

    if debug > 1:
        print("\n"+"Instancio OBJETO Template_tcg con archivo: "+str(archivo_tcg)+"\n")

    template = Template_tcg(archivo_tcg)
    separador=",;,"


    print("--------------------------------INICIOxx:" + str(element) + " --------------------------------------")
    #para todos los grupos del tempalte

    if debug > 0:
        print("Armo el patron en todas las lineas tcg de grupos con variables otf (Grupos):")

    for g in template.groups:
        config_grupo=""
        secuencia_reg_exp = 0

        if debug > 1:
            print("Relevo Grupo:"+str(g))



        lines_tcg_g = template.get_tcg_by_group(g)
        #print("VARIABLE del GRUPO: "+str(template.get_var_by_group(g)))
        
        var_es_regexp=False # esto es true si una OTF de un grupo solo aparece una vez y por lo tanto es una regexp que no precisa relacionarse
                            #  esto es necesario solo en lineas optativas donde no se genera el patron que inicializa la variable relacionada 
                            #  sino que espera que ya este generada con ese label en otra linea
        
        for var_otf in template.get_var_by_group(g):
        # para cada variables otf de dicho grupo

            print(str(g))
            print(str(var_otf["variable_name"]))
            var_es_regexp = template.otf_de_grupo_es_regexp(var_otf["variable_name"],g)

            if debug > 1:
                print("		Tomo variable OTF del grupo "+str(g)+" : "+str(var_otf))
                print("\n")

            g_reg_exp_generado = False
            # necesito saber como queda regular expresion escapeada para poder identificarla en el tcg y manipular esa parte del texto
            exp_regular_esp = var_otf["exp_regular"]
            exp_regular_esp=escape_string_exception(exp_regular_esp)
            #print("Expresion regular de esa var luego de poner los \\:")
            #print(str(exp_regular_esp))




            for lin_g in lines_tcg_g:
                if debug > 1:
                    print("				Render del patron asociado a la variable OTF sobre linea TCG del grupo: ")
                    print("				"+str(lin_g.patron))


                #print("Itero lineas tcg asociadas al grupo:" + g)
                #print("Linea: "+str(lin_g.patron))
                #barro todas las lineas tcg perteneciente al grupo y reemplazo la variable otf por su expresion regular
                # tambien tener en cuenta que la expresion regular en el patron se define solo la primra vez y luego se referencia el grupo original por ejemplo (\1)
                if var_otf["exp_regular"]=="":
                    print("***** ERROR **** - no deberia tener nunca una expr reg vacia")
                    # # entonces no teniua una exp regular especificada, debo cargar la default
                    # #pero debo revisar tambien si ya la volque al patron, sino en vez de poner reg_exp debo poner la referencia de grupo ej (\1)
                    # #print("la variable no tiene una expr_reg explicita")
                    # if not g_reg_exp_generado:
                    # 	#guardo estado linea patron antes de intentar el replace
                    # 	lin_g_patron_prev=lin_g.patron
                    # 	lin_g.patron=lin_g.patron.replace(str(var_otf["variable"]),"(?P<"+str(var_otf["variable_name"])+">\\S+)")
                    # 	# este lo uso despues para para extrar config candidata a pertencer al grupo (o sea no uso las llamadas del grupo)
                    # 	#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!igual no sirce porque si dos variables en una linea no queda resuelto, hacelo despues de barrer variables
                    # 	lin_g_patron_first=lin_g.patron
                    # 	#print("line patron prev:")
                    # 	#print(str(lin_g_patron_prev))
                    # 	#print("line patron added regex:")
                    # 	#print(str(lin_g.patron))
                    # 	if lin_g_patron_prev != lin_g.patron:
                    # 		#print("cambio asique marco que ya aplique nombre de regexp")
                    # 		#Si cambio algo entonces fue poruqe hubo matcheo, la proxima uso ref a grupo (\1)
                    # 		g_reg_exp_generado=True
                    # else:
                    # 	lin_g.patron=lin_g.patron.replace(str(var_otf["variable"]),"(?P="+str(var_otf["variable_name"])+")")

                    # 	#print("Ya inicialize grupo de reg expr asique solo la referencio:")
                    # 	#print(str(lin_g.patron))

                else:
                    # tiene expresion regular explicita porque lo construyo asi
                    #print("la variable tiene una expr_reg explicita")
                    if (not g_reg_exp_generado) and (not lin_g.optative):  ## excluyo optativas porque no pueden inicializar OTF, asique nunca deben entrar aca, solo pueden usar una otf inicializada por otra linea
                        lin_g_patron_prev=lin_g.patron
                        #reemplazo por expr regular con primera aparicion del grupo
                        #en el patron puede figurar tanto explicita como no asique reemplazo considerando ambos casos
                        #tambien reemplazo funcion por regexp general, para que no condicione match del grupo, se ejecuta despues la funcion con la otf ya obtenida
                        #aaa (?P<varNO>\S+)<--\(VAR\.\) aaa (?P<VAR2>\S+)

                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--f_"+str(var_otf["funcion2"])+"\\("+str(var_otf["parametro1"])+","+str(var_otf["parametro2"])+"\\)","(?P<"+str(var_otf["variable_name"])+">"+str(var_otf["exp_regular"])+")")
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--f_"+str(var_otf["funcion"])+"\\("+str(var_otf["parametro"])+"\\)","(?P<"+str(var_otf["variable_name"])+">"+str(var_otf["exp_regular"])+")")
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--\\("+str(exp_regular_esp)+"\\)","(?P<"+str(var_otf["variable_name"])+">"+str(var_otf["exp_regular"])+")")
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"]),"(?P<"+str(var_otf["variable_name"])+">"+str(var_otf["exp_regular"])+")")
                        
                        #print("PATROOOONN_2: "+lin_g.patron)
                        #############################################lin_g_patron_first=lin_g.patron
                        #print("line patron prev:")
                        #print(str(lin_g_patron_prev))
                        #print("line patron added regex:")
                        #print(str(lin_g.patron))
                        if lin_g_patron_prev != lin_g.patron:
                            #print("cambio asique marco que ya aplique nombre de regexp")
                            #Si cambio algo entonces fue poruqe hubo matcheo, la proxima uso ref a grupo (\1)
                            g_reg_exp_generado=True
                    elif not var_es_regexp:
                        #print(str(lin_g.patron))
                        #reemplazo por expr regular referenciado el grupo ya definico
                        #en el patron tcg puede figurar tanto explicita como no asique reemplazo considerando ambos casos
                        #print("en: "+lin_g.patron+ "reemplazo:" + str(var_otf["variable"])+"<--\\("+str(exp_regular_esp)+"\\)")
                        #print ("por: "+ "(?P="+str(var_otf["variable_name"])+")")
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--f_"+str(var_otf["funcion2"])+"\\("+str(var_otf["parametro1"])+","+str(var_otf["parametro2"])+"\\)","(?P="+str(var_otf["variable_name"])+")")
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--f_"+str(var_otf["funcion"])+"\\("+str(var_otf["parametro"])+"\\)","(?P="+str(var_otf["variable_name"])+")")
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--\\("+str(exp_regular_esp)+"\\)","(?P="+str(var_otf["variable_name"])+")")
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"]),"(?P="+str(var_otf["variable_name"])+")")
                        #print("Ya inicialize grupo de reg expr asique solo la referencio:")
                        #print(str(lin_g.patron))

                    elif var_es_regexp:
                        # la otf aparece solo una vez dentro de grupo, asiuqe la trato como reg_exp independiente en el patron
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--f_"+str(var_otf["funcion2"])+"\\("+str(var_otf["parametro1"])+","+str(var_otf["parametro2"])+"\\)",str(var_otf["exp_regular"]))
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--f_"+str(var_otf["funcion"])+"\\("+str(var_otf["parametro"])+"\\)",str(var_otf["exp_regular"]))
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"])+"<--\\("+str(exp_regular_esp)+"\\)",str(var_otf["exp_regular"]))
                        lin_g.patron=lin_g.patron.replace(str(var_otf["variable"]),str(var_otf["exp_regular"]))

            #            lin_g.patron_no_esc=lin_g.patron_no_esc.replace(str(var_otf["variable"])+"<--\\("+str(exp_regular_esp)+"\\)",str(var_otf["exp_regular"]))
            #            lin_g.patron_no_esc=lin_g.patron_no_esc.replace(str(var_otf["variable"]),str(var_otf["exp_regular"]))

                        #mas adelante voy a usar patron_no_esc (el cual no fue modificado durante este proceso) para aplicar los otf
                        #deducidos y cruzarlo con el texto, sin embargo estos casos no va a tener un otf deducido
                        #asique aprovecho este paso y modifico el prton_no_esc en estas lineas solo para estas variables
                        # mantengo la expr_regular que aplico sin escapear porque al generar nuevasotf las escapeas automatiamente
                        #..........


                if debug > 1:
                    print("				Patron resultante actualizado con reg_exp en el tcg (en atributo patron): ")
                    print("				"+str(lin_g.patron))
                    print("\n")

    #//////// hasta aca podria estar en clase constructora si lo armas distinto???? 

    #print("Barri todos los Grupos, tengo patrones de las lineas tcg en formato expr_regular en vez de en formato TCG")

    if debug > 0:
        print("-------------  Levanto Archivo de configuracion  (no objeto Config aun) -------------")

    #!!!!!!!!!XXXXX  tengo que restringir config a candidatos del grupo antes de aplanarla en una linea
    #!!!!!!!!!XXXXX  y tengo que repetirlo con cada grupo

    #print("Levanto arch config -------------------------------")
    config_completa=""
    with open(archivo_cfg, errors='replace') as file_input: 
        conf_data = file_input.readlines()
        for linea_confg in conf_data:
            linea_confg=linea_confg.strip()

            if debug > 2:
                print(str(linea_confg))

            config_completa=str(config_completa)+separador+str(linea_confg)+separador

    #print("------------config sacada de archivo a duplicar:")
    if debug >2:
        print("----------------Configuracion convertida en una linea y con separadores---------------")
        print(str(config_completa))

    # replico la config tantas veces como lineas tenga el grupo de manera de poder satisfacer cualquier orden de aparicion de las lineas
    ##print("Config_grupo::::::")
    ##print(config_grupo)


    for g in template.groups:

        if debug > 1:
            print("Proceso grupo: "+str(g))


        #print("----------------------Grupo:"+str(g))
        if g in template.optative_groups:
            grupo_es_optativo=True
            #print("El grupo es OPTATIVO")
        else:
            grupo_es_optativo=False
            #print("El grupo es NOOO OPTATIVO")
        lines_tcg_g = template.get_tcg_by_group(g)
        config_grupo_incr=config_completa
        config_grupo=""
        #print("Cant de lineas tcg en grupo = "+str(len(lines_tcg_g)))

        ###################<-----------------------------------------------------!!!!!!!!!


        #################   TAG RETOMO

        # aca deberia tomar solo las lineas de configuracion pertenecientes al grupo g y no toda la config
        # pone ese fragmento de config en config_grupo_incr
        # para eso voy a generalizar el patron con (.*) para que matchee cualquier caso potencial como parte del grupo 
        # y a guardar el fragmento de la config como config_parcial_grupo para aplicarle la resolucion del grupo solo a estas lineas

        #print("Levanto arch config -------------------------------")
        config_parcial_grupo=",;,l,;,,;,l,;,"+separador  # esto lo tuve que forzar cuando arrancaba config sin lineas adicionales, ?
        with open(archivo_cfg) as file_input:
            conf_data = file_input.readlines()
 ##D        with open(archivo_cfg) as file_input:
 ##D            conf_data2 = file_input.read()

 #---------------

        for linea_confg in conf_data:
                ##########!!sacar#####
  #                print("grupo:"+str(g)+"-- linea: "+linea_confg)
            linea_confg=linea_confg.strip()
            line_config_potencial=False
            for linea_tcg_de_grupo in lines_tcg_g:
                if debug > 2:
                    print("linea patron generico: "+str(linea_tcg_de_grupo.patron_generico))
                match_lg = re.match(linea_tcg_de_grupo.patron_generico,linea_confg)
                if match_lg:
  #                    print("hubo match la incluyo")
                    line_config_potencial=True
            if line_config_potencial:
                config_parcial_grupo=str(config_parcial_grupo)+separador+str(linea_confg)+separador


        #piso esta porque ya no uso la config completa sino la parcial candidata para ese grupo
        #se queres hacer un rollback de esto , solo comenta la siguiente linea
        config_grupo_incr=config_parcial_grupo

 #---------------
        #######################



        if debug > 1:
            print("		Clono la configuracion "+ str(len(lines_tcg_g)) +" veces")

  ###### Grados de libertad, aca comente los grados de libertad y los foce para que no clone la config
     #!#   for i in range(0,len(lines_tcg_g)):
        for i in range(0,1):
            config_grupo=config_grupo+config_grupo_incr
     #   config_grupo+=config_grupo+config_grupo_incr

        # #print("config del grupo clonada: ------")
        # #print(config_grupo)
        # #print("fin config clonada ------")

        config_grupo=config_grupo+",;,l,;,"  #  con sumar ",;," alcanzaba

        if debug > 1:
            print("Configuracion parcial candidata para aplicar parseos del GRUPO: "+str(g))
            print(config_grupo)

        #concateno lineas tcg para armar secuencia de matcheo del grupo separadas por separador
        patron_grupo=""

        for linea_grupo in template.get_tcg_by_group(g):
            #solo lo incluyo en patron de busqueda si no es optativo (la linea) y si no es optativo todo el grupo (ahi cambia el significado del optativo de la linea y hay que incluirla en el match)
            # si bien no usa la linea optativa para deducir la otf despues si la uso al instaciar el grupo para las comparaciones
            # lo que no puede hacer una linea optative es generar una otf es decir usar una [[var]] sin que se la inicie otro
            if not linea_grupo.optative or grupo_es_optativo:
                ##print("linea patron:"+str(linea_grupo.patron))
                if patron_grupo == "":
                    patron_grupo="[\s\S]*"+separador+str(linea_grupo.patron)+separador
                else:
                    patron_grupo=str(patron_grupo)+separador+"[\s\S]*"+str(linea_grupo.patron)



        patron_grupo = str(patron_grupo)+separador+"[\s\S]*"
        #print("Patron del grupo")
        #print(patron_grupo)
        if debug > 1:
            print("		Armo patron del grupo con los patrones de las diferentes tcg del grupo (no incluye clausulas optativas): "+str(g))
            print("		con estos patrons solo voy a deducir los otf")
        if debug > 1:
            print("		"+str(patron_grupo))
        #print("CONIF a MATECHEAR:")
        #print(config_grupo)


        #hago el match para hallar las otf, para esto busco patron_grupo en config_grupo(ya clonada)
        #match=re.findall(patron_grupo,config_grupo,re.MULTILINE)
        #match=re.findall(patron_grupo,config_grupo,re.MULTILINE)

        #print("Match::::::::::::: para grupo  " + str(g))

        # solo avanzo ageneracion de grupo de instancia si el grupo tiene alguna OTF

        if debug > 1:
            print("		Si el grupo "+str(g)+" tiene variables OTF procedo a deducirlas, sino avanzo a siguiente")
        if len(template.get_var_by_group(g))>0:
            #print("eeeeentro a procesar grupo:" +str(g))
            #print(str(template.get_var_by_group(g)))
            seguir = True
            instancia=1

            # genero el copile del patron de para ese este grupo 
            pattern = re.compile(patron_grupo)

            while seguir:

                if debug > 1:
                    print("\n")
                    print("		Busco si el patron del grupo matchea con alguna linea de la config (remanente)")

                # Comente esta linea y habilite las dos linea que dicen pattern para usar la regexp compilada y compilarla solo una vez (fuera del while)
                # No se percibe mejora significativas y  no se ve perdida de funcionalidad
                #m=re.match(patron_grupo,config_grupo,re.MULTILINE)

                m = pattern.match(config_grupo,re.MULTILINE)

                if m :
                    #print("hubo match")
                    if debug > 1:
                        print("		Hubo Match, teniendo los valores deducidos de las OTF, barriendo cada linea del grupo genero un nuevo grupo instanciado:")
                    for linea_grupo in template.get_tcg_by_group(g):
                        #print("FOR linea_grupo :--------------------"+ linea_grupo.patron_no_esc)
                        if debug > 1:
                            print("				Para cada linea tcg del grupo: ")
                            print("				"+str(linea_grupo.patron_no_esc))
                        patron_new_instancia_grupo = linea_grupo.patron_no_esc
                        
                        #---------------------------------------funciones ------------------------------
                        # elimino referencia a funciones
                        #el valor obtenido otf candidato de la funcion no me sirve, ya que toma el primero que matchee /S+
                        # sin fijarse en funcion, es decir que el obtenido puede no matchear funcion pero otro existente en la config si matchear
                        # asique aca tengo que resolver funcion para generar lineas tcg completas y luego verificar el ok del grupo
                        # en la resolucion de directivas como si esto fuera un literal 


                        if debug > 1:
                            print("						Resuelvo las funciones embebidas en dicha linea ")

                        for v_func in linea_grupo.get_variables_a_deducir():
                            #barro las variables del tipo funcione de esta linea del grupo
                            # resulevo las funciones de un solo parametro (las de dos parametros estaran en funcion2)
                            if v_func["funcion"] != "":

                                result=""
                                param = v_func["parametro"]
                                input_f = m.group(param)  ######  aca inyecto valores deducidos (OTF)

                                ###################  listado funciones de 1 parametro  #################

                                if v_func["funcion"] == "NextIP":
                                    result=NextIP(input_f)

                                ########################################################################

                                    if debug > 1:
                                        print("\n")
                                        print("						Funcion de 1 parametro: "+str(v_func["funcion"]))
                                        print("						parametro: "+str(param)+" valor_parametro: "+str(input_f) + " Resultado= "+str(result))

                                else:
                                    print("ERROR: Se invoco una funcion inexistente: "+str(v_func["funcion"]))
                                #reemplazo la llamada a la funcion por su valor resuelto
                                patron_new_instancia_grupo= re.sub("\[\["+v_func["variable_name"]+"\]\]<--f_"+v_func["funcion"]+"\("+param+"\)",str(result),patron_new_instancia_grupo)
                        #repito lo mismo pero para funciones de dos variables:

                        for v_func in linea_grupo.get_variables_a_deducir():
                            #barro las variables del tipo funcione de esta linea del grupo
                            # resulevo las funciones de un solo parametro (las de dos parametros estaran en funcion2)
                            if v_func["funcion2"] != "":

                                result=""
                                param1 = v_func["parametro1"]
                                param2 = v_func["parametro2"]
                                input_f1 = m.group(param1)
                                input_f2 = m.group(param2)


                                ###################  listado funciones de 2 parametros  #################

                                if v_func["funcion2"] == "FuncionDePrueba2":
                                    result=FuncionDePrueba2(input_f1,input_f2)

                                ########################################################################

                                    if debug > 1:
                                        print("\n")
                                        print("						Funcion de 2 parametro: "+str(v_func["funcion2"]))
                                        print("						parametros: "+str(param1)+","+str(param2)+" valores_parametro: "+str(input_f1)+","+str(input_f2) + " Resultado= "+str(result))


                                else:
                                    print("ERROR: Se invoco una funcion inexistente o  mal parametrizada: "+str(v_func["funcion2"])+" requiere dos parametro")


                                #reemplazo la llamada a la funcion por su valor resuelto
                                patron_new_instancia_grupo= re.sub("\[\["+v_func["variable_name"]+"\]\]<--f_"+v_func["funcion2"]+"\("+param1+","+param1+"\)",str(result),patron_new_instancia_grupo)



                        #------------------------------------------------ fin funciones --------


  ###########
                    

  ###########


                        for ky in m.groupdict().keys():
                            valor=m.group(ky)
                            #print(str(ky)+":"+str(valor))

                            # elimino las referencias a regex especificas
                            # y genero el texto de esa nueva tcg con el otf obtenido, texto mas directivas necesito simular			
                            patron_new_instancia_grupo = re.sub("\[\["+str(ky)+"\]\]",str(valor),patron_new_instancia_grupo)

                        # elimino las referencias a regex especificas de otf que ya resolvi y quedaron sin [[]]
                        # pero solo las que resolvi, es decir <--() sin el [[]] antes, ya que las que era expresiones regulares puras
                        # que no se instanciaron (como las de O) y no tengo un valor de otf, entonces necesito mantener el <-- para tratarla
                        #luego como expresion regular directa

                        patron_new_instancia_grupo= re.sub("]<--\(","]<-,;,-\(",patron_new_instancia_grupo)
                        patron_new_instancia_grupo= re.sub("<--\(\\S+?\)","",patron_new_instancia_grupo)
                        patron_new_instancia_grupo= re.sub("]<-,;,-\(","]<--\(",patron_new_instancia_grupo) 


                            
                        first=True
                        directivas_new=""
                        for dd in linea_grupo.directivas:
                            if dd==g:
                                if first:
                                    directivas_new=str(g)+"#"+str(instancia)
                                    first=False
                                else:
                                    directivas_new=str(directivas_new)+","+str(g)+"#"+str(instancia)  ## rename de la directiva de grupo
                            else:
                                if first:
                                    directivas_new=str(dd)
                                    first=False
                                else:
                                    directivas_new=str(directivas_new)+","+str(dd)
                        # genero una nueva linea_tcg_para ir formando la_instancia_del_grupo
                        

                        if debug > 1:
                            print("				----- Genero para esta linea una line nueva del grupo instanciado:--")
                            print("				"+patron_new_instancia_grupo+" ("+directivas_new+")")
                            print("\n")

                        linea_new_tcg_inst_grupo = Linea_tcg(patron_new_instancia_grupo+" ("+directivas_new+")")
                        # cada nueva linea tcg de la instanciacion del grupo la sumo al template
                        template.lineas_tcg.append(linea_new_tcg_inst_grupo)
                        # agrego los grupos nuevos al listado de grupos
                        grupo_inst= str(g)+"#"+str(instancia)

                        #print("patron new tcgl" + linea_new_tcg_inst_grupo.patron)
                        #print("patron_no_esc new tcgl" + linea_new_tcg_inst_grupo.patron_no_esc)
                        

                        #hago listado aparte de grupos nuevos instanciados y fuera del loop despues los sumoa tempalte.groups asi tiene todos
                        # ahora no puedo agregarlo a groups sino impacta sobre el for sobre el que estoy trabajando
                        if grupo_inst not in template.groups_instanciados:
                            template.groups_instanciados.append(grupo_inst)

                        #print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
                        #print("grupos new: "+ str(template.groups))

                        #print("AGREGUEEEEE a template instacia grupo:  "+ patron_new_instancia_grupo+" ("+directivas_new+")")
                        #elimino esa intancia de la config para volver a buscar siguientes instancia de matcheo del grupo
                        # OJOOOO aca si necesito que este escaped los caracteres esp de reg_exp!!!!
                        patron_new_instancia_grupo_escp=escape_string(patron_new_instancia_grupo)
                        #elimino el match que enocntre de la config del grupo, pero solo si tiene variables otf
                        #si es un literal lo tengo que dejar para que siga estando en proxima instancia 
            
                        if debug > 1:
                            print("				Borro matcheo de configuracion para buscar siguiente match (pero solo si no es un literal y no es shared)")

                        if linea_grupo.get_variables_a_deducir()!=[] and not linea_grupo.shared:
                            #print("::::---- linea_grupo (escapeada) a eliminar::"+ patron_new_instancia_grupo_escp)
                            config_grupo=re.sub(str(separador)+patron_new_instancia_grupo_escp+str(separador),"",config_grupo)
                    instancia=instancia+1

                else:
                    if debug > 1:
                        print("no more match en el grupo")
                    seguir = False



        # tengo las instanciad de los grupos resueltas con sus OTF completas, no tngo que usar las lineas_tcg que 
        # tengan variables a deducir porque ya estan en estos casos instanciadas

    #################### FIN DEDUCCION OTF de GRUPOS########################################################################################

    if debug > 0:
        print("#############  FIN de DEDUCCION de valores de las variables OTF de los GRUPOS   ####################################")
        print("####################################################################################################################")

    if debug > 0:
        print("------------------ Resuelvo las variables OTF que no estan dentro de un grupo--------- ")
        print("Estas NO toman un valor, solo adecuo el patron de la linea con la rex_exp de la variable otf que debera cumplir")
        print("\n")

    # tomo linea y resulevo las variables OTF por linea (sin grupo) es decir la expreion regular

    if debug > 1:
        print ("Resultante luego de ajustar patron de lineas no pertenecientes a un Grupo:")

    for xlinea_tcg in template.lineas_tcg:
        if not xlinea_tcg.group and not xlinea_tcg.comentario:
            for otf_exp_reg in xlinea_tcg.get_variables_a_deducir():
                #print("Proceso tcg :"+ xlinea_tcg.patron)
                #print("LLLLLLLLLLLLLLinea con OTF y sin grupo: "+str(otf_exp_reg))
                g_reg_exp_generado = False
                # necesito saber como queda regular expresion escapeada para poder identificarla en el tcg y manipular esa parte del texto
                exp_regular_esp = otf_exp_reg["exp_regular"]
                exp_regular_esp = escape_string_exception(exp_regular_esp)

                xlinea_tcg.patron=xlinea_tcg.patron.replace(str(otf_exp_reg["variable"])+"<--\\("+str(exp_regular_esp)+"\\)","(?P<"+str(otf_exp_reg["variable_name"])+">"+str(otf_exp_reg["exp_regular"])+")")
                xlinea_tcg.patron=xlinea_tcg.patron.replace(str(otf_exp_reg["variable"]),"(?P<"+str(otf_exp_reg["variable_name"])+">"+str(otf_exp_reg["exp_regular"])+")")
                #print("cambio patron :"+xlinea_tcg.patron)
                if debug > 1:
                    print(xlinea_tcg.patron)


    ############################################################################################################
        ######################################################3
        # inicio tratamiento de directivas  ##################
        ######################################################

    #print("####################################################################################################")
    #print("#############################inicio tratamiento de directivas#######################################")

    if debug > 0:
        print("##################  Inicio tratamiento de Directivas  ########"+"\n")

    if debug > 1:
        print("\n"+"Instancio OBJETO Config_cfg usando archivo: "+ str(archivo_cfg) +"\n")

    config = Config_cfg(archivo_cfg)


    #print(" #################  tratamienti Directivas GRUPOS resueltos ##################")
    ###########################################
    ###  GRUPOS ##############################

    # ahora si los junto para que esten todos en groups
    template.groups=template.groups+template.groups_instanciados

    ## si un grupo no tiene otf entonces no va a ser instanciado y solo puede tener o no una aparicion en la configuracion
    ## esos grupos debe ttener su tratamiento propio
    ## estos casos podrian tener logica de directivas adicionales y ser menjados de manera sencilla


    ## si un grupo tiene OTF, el hecho de que este instanciado significa que existe en la config
    ## por lo que la existencia o no de una o mas instancias indicara si cumplio o no el  mandatorio
    ## y solo restara marcar las lineas de la config <-- falso, hay que verificar si sigue siendo valido tras el calculo de 
    ## las funciones y por otro lado podrian agregarse otras directivas (no condicionantes del match para deduccion de otf)
    ## x ejemplo una linea optativa, en el match ni se considera

    ## pruebo de darle mismo trato que a los no instanciados, solo dejo afuera los originales que generaron los instanciados 

    #print("GRUPOSSSSS no instaciasdos e instanciados resueltos:::")
    #barro grupos

    if debug > 0:
        print("Barro  grupos originales sin OTF y los de OTF instanciados(que ya no tienen OTF):")

    for gg in template.groups:
        #print("grupo: "+str(gg))
        m_instanciado = re.match(r'G_\S+#\d+',str(gg))

        if debug > 1:
            print("GRUPO: ",str(gg))
    #		if m_instanciado:
    #			print("		es instanciado")

        # voy a tomar solo grupos otf instaciados y voy a fijarme que variables les quedaron, esas deben se tratadas como exp-reg dentro de las tcg, se arrastran de (O) que no fueron instanciados
        mgi = re.search("#",gg)
        if mgi:
            array_varx = template.get_var_by_group(gg) #tomo variables pendientes del grupo otf nuevo instanciado
            for vargg in array_varx:  # las recorro
                exp_regular_espx = vargg["exp_regular"]
                exp_regular_espx = escape_string_exception(exp_regular_espx)
                print(exp_regular_espx)
            
                print(str(vargg))
                for lvar in template.get_tcg_by_group(gg):
                    print(lvar.patron)

                    lvar.patron=lvar.patron.replace(str(vargg["variable"])+"<--\\("+str(exp_regular_espx)+"\\)","(?P<"+str(vargg["variable_name"])+">"+str(vargg["exp_regular"])+")")
                    lvar.patron=lvar.patron.replace(str(vargg["variable"]),"(?P<"+str(vargg["variable_name"])+">"+str(vargg["exp_regular"])+")")
                    print("cambio patron :"+lvar.patron)

        print("----------"+str(template.get_var_by_group(gg)))

        # trabajo solo sobre los grupos originales SIN OTF y los ya instanciados
        if mgi or template.get_var_by_group(gg)==[] :
        ####if template.get_var_by_group(gg)==[]:          #and not m_instanciado:
            if debug > 0:
                print("		Grupo: "+str(gg)+"---------------------------------------------")
            #print("		No tiene OTF - Ingreso a trabajar este grupo: "+str(gg))
            m_failed = False
            grupo_incompleto = False
            
            if not mgi: # en realidad si esta instanciado ya sabes que es un grupo que esta completo dentro de config, sino la regexp no hubiera generado
                        #el grupo intsanciado, asique solo verifico si completo los grupos que no tuvieron otf

                #tomos todas las lineas de ese grupo
                for g_tcg_linea in template.get_tcg_by_group(gg):

                    if debug >1:
                        print("				Linea de grupo "+str(gg)+" (patron_no_esc):")
                        print("				"+str(g_tcg_linea.patron_no_esc)+"\n")
                        print("				patron: "+str(g_tcg_linea.patron)+"\n")

                    #print("lineas del grupo : "+g_tcg_linea.patron_no_esc)
                    linea_g_esta_en_config=False
                    # barro lineas del archivo de configuracion
                    for linea_cfg in config.lineas_cfg:


                        #print("lineas arch config: "+linea_cfg.texto)

                        #!!!!!!!!!!! estos  == lo tengo que reemplazar por matcheo que contemple expr regulares
                        #if str(g_tcg_linea.patron_no_esc)==str(linea_cfg.texto):
                        #	#print("HIZO MATCH POR COMPARACION ==")
                        #	#print("linea tcg E es igual a linea config")
                        m=re.match("^"+str(g_tcg_linea.patron)+"$",linea_cfg.texto)
                        if m:

                            if debug > 1:
                                print("				Hizo un MATCH en Confiuguracio")

                            #print("HIZO MATCH POR EXPREG")
                            #print("linea tcg de grupo es igual a linea config")
                            linea_g_esta_en_config=True
                            break
                    if not linea_g_esta_en_config:
                        # esa line del grupo no figura en config
                        #print("esa line del grupo no figura en config")


                        if debug > 1:
                            print("				NO MATCH en Configuracion")


                        if not g_tcg_linea.optative or (gg in template.optative_groups):

                            if debug > 1:
                                print("				La line es Mandatoria en el grupo -> Grupo INCOMPLETO") 
                                print("				(no se si mandatory_failed aun, o si pass etc)")

                            #si la linea no es optativa o si es optativa pero a nivel grupo, entonces marco grupo como incompleto
                            grupo_incompleto=True
                            break

            ## Ahora si es valido el grupo entonces tengo que marcar como validas las lineas en la config
            if not grupo_incompleto:

                if debug > 1:
                    print("		Grupo "+str(gg)+" COMPLETO")
                    print("		Marco las linea en la Config como VALIDADAS")

                for gg_tcg_linea in template.get_tcg_by_group(gg):
                    # barro lineas del archivo de configuracion
                    for linea_cfg in config.lineas_cfg:
                        m=re.match("^"+str(gg_tcg_linea.patron)+"$",linea_cfg.texto)
                        if m:
                            #print("line validada")

                            if linea_cfg.estado!="negada":
                                    linea_cfg.estado="validada"				

                            if debug > 1:
                                print("						linea de config validada: "+str(linea_cfg.texto))

                            if gg_tcg_linea.warning:
                                linea_cfg.warning=True

                                if debug > 1:
                                    print("						linea con WARNING")
                            
                            if gg_tcg_linea.literal:  #  si es literal y no tiene regex entonces solo aplica auna linea en config, asique ya salgo y no barro toda las demas lineas de la config
                                break  # en realidad aca solo llegan las Optativas de grupo, las otras fueron resueltas de manera lietral por la regexp y con eso se creo la nueva instancia
                                       # y ademas exclusivamnete las Optativas de grupo que no invoquen una OTF resuleta por el grupo, es decir las de regexp puras

                if debug > 1:
                    print("		Sumo el grupo ORIGINAL de "+str(gg)+"al listado de grupos que Matceharon al menos una vez (instancia) en config")

                # Y tambien tengo que registrar que esta instancia valido grupo padre en caso de ser mandatorio
                if gg not in template.groups_padre_validados and m_instanciado:
                    g_orig= gg.split("#")[0]
                    template.groups_padre_validados.append(g_orig)

            if grupo_incompleto and not m_instanciado:

                if debug > 0:
                    print("		Grupo "+str(gg)+" dio INCOMPLETO, por lo tanto:")


                # si el grupo entero no es optativo (y no es instanciado ya que una instancia no define al grupo padre)
                if gg not in template.optative_groups:

                    if debug > 0:
                        print("				Grupo NO optativo, asique lo agrego a lista de grupos Mandatory_failed ")
                        print("				Marco todas las lineas de configuracion del grupo como mandatory_failed")
                        print("				Envio syslog si tiene tag de TRAP")
                    #if not g_tcg_linea.optative:
                    m_failed=True
                    # agrego grupo a listado de grupos mandatory failed
                    if gg not in template.mandatory_failed_groups:
                        template.mandatory_failed_groups.append(gg)
                        # marco todas las lineas del grupo como mandatory failed
                        for g_tcg_linea_2 in template.get_tcg_by_group(gg):
                            g_tcg_linea_2.mandatory_failed=True
                            if g_tcg_linea_2.trap != "":				
                                facility = "COMPLIANCE"
                                message = "Mandatorio no cumplido :"+str(g_tcg_linea_2.texto)
                                severity = g_tcg_linea_2.trap.replace("TRAP_","")
                                send_tambo_event(OWNER=owner,ELEMENT=element,FACILITY=facility,SEVERITY=severity,MESSAGE=message)
                                #print("ENVIO SYSLOG:"+str(facility) + "-" + str(severity) + "-" + str(message))	

                                if debug > 1:
                                    print("				Envio syslog - TAG: "+str(severity))
                                    print("				mensage: "+str(g_tcg_linea_2.texto))
        else:
            if debug > 1:
                print("no lo proceso")

    if debug > 0:
        print("########  Finalice analisis directivas grupos no instanciables y no instanciados (sin variables OTF)####")
        print("\n")
        print(" ---  INICIO analisis directivas de Grupos instanciables Originales --- ")
        print(" --- (Aca solo identifica grupos mandatorios que no tuvieron ninguna ocurrencia/instancia) ")

    # ahora solo resta recorrer los grupos originales instanciables, y ver si alguno es mandatorio y no fue satisfecho
    #por ninguna de sus instancias y completar la listas de groups_mandatory_failes para el reporte
    for gg in template.groups:
        # trabajo solo sobre los grupos originales con OTF

        if template.get_var_by_group(gg)!=[]:

            if debug > 1:
                print("Analizo Grupo: "+str(gg))

            if gg not in template.optative_groups:
                if gg not in template.groups_padre_validados:

                    if debug > 1:
                        print("NO es un grupo optativo y no figura validado por un grupo instanciado hijo")
                        print("Lo sumo a lista de MANDATORY_FAILED_GROUP")

                    template.mandatory_failed_groups.append(gg)


    if debug > 1:
        print("\n")
        print("Lista final de Grupos mandatory failed:")
        print(str(template.mandatory_failed_groups))

    #print("# EXCLUSIVE X LINEA ##############################")
    ###########################################
    # EXCLUSIVE X LINEA ##############################


    if debug > 0:
            print("---------  Analizo grupos E (EXCLUSIVE) -------------------------"+"\n")

    #barro todos los grupos exclusive del tempalte
    for ee in template.exclusives:

        if debug > 1:
            print("Grupo EXCLUSIVE: "+str(ee))

        #print("grupo E:" + str(ee))
        m_failed = False
        cumple_linea=""
        linea_cfg_cumple=""
        #tomos todas las lineas de ese grupos excluusive
        for e_tcg_linea in template.get_tcg_by_exclusive(ee):
            #print("lineas del grupo de E: "+e_tcg_linea.patron_no_esc)

            # barro lineas del archivo de configuracion
            for linea_cfg in config.lineas_cfg:
                #print("lineas arch config: "+linea_cfg.texto)
                #!!!!!!!!!!! estos  == lo tengo que reemplazar por matcheo que contemple expr regulares
                #if str(e_tcg_linea.patron_no_esc)==str(linea_cfg.texto):
                    #print("HIZO MATCH POR COMPARACION ==")
                    #print("linea tcg E es igual a linea config")
                m=re.match("^"+str(e_tcg_linea.patron)+"$",linea_cfg.texto)
                if m:
                    #print("HIZO MATCH POR EXPREG")
                    #print("linea tcg E es igual a linea config")
                    if cumple_linea != "":
                        # ya matcheo => no es exclusive
                        # MADATORY_FAILED para el grupo exclusive ee
                        #print("Falla mandatorio grupo E no exclusivo: "+str(ee))
                        m_failed=True


                    else:
                        # registro info de linea que matchea

                        cumple_linea=linea_cfg.texto
                        linea_cfg_cumple = linea_cfg
                        #print("MMMMMMMMatch legitimo: "+ linea_cfg_cumple.texto)
                        #ya encontre un match, no necesito completar archivo de config
                        break


        if cumple_linea == "" or m_failed:
            # no hubo ningun match o dio repetido (si dio repetido por mas que sea Optativa es un desvio)

            if debug > 1:
                print("	Grupe Exclusive no tuvo match o tuvo mas de uno (no exclusivo)")


            if e_tcg_linea.optative and not m_failed:

                if debug > 1:
                    print("		Es optativo asique no afecta, pasa de largo sin validar config")

                # es un exclusive optativo, no pasa nada
                #print("no cumple E pero no es mandatorio")
                pass

            else:
                # es un exclusive mandatorio
                # MADATORY_FAILED para el grupo exclusive ee
                #print("Falla mandatorio grupo E: "+str(ee))
                # marco todas sus tcg como failed

                if debug > 1:
                    print("		Es Mandatorio asique es un Mandatory_failed:")
                    print("		Lo sumo a lista de mandatory_failed_exclusives")
                    print("		Marco las lineas del tcg como mandatory_failed")
                    print("		Enio syslog si tiene marca de TRAP ")

                if ee not in template.mandatory_failed_exclusives:
                    template.mandatory_failed_exclusives.append(ee)

                for e_tcg_linea_2 in template.get_tcg_by_exclusive(ee):
                    e_tcg_linea_2.mandatory_failed=True
                    if e_tcg_linea_2.trap != "":
                                facility = "COMPLIANCE"
                                message = "Mandatorio no cumplido :"+str(e_tcg_linea_2.texto)
                                severity = e_tcg_linea_2.trap.replace("TRAP_","")
                                send_tambo_event(OWNER=owner,ELEMENT=element,FACILITY=facility,SEVERITY=severity,MESSAGE=message)
                                #print("ENVIO SYSLOG:"+str(facility) + "-" + str(severity) + "-" + str(message))	
                                if debug > 1:
                                    print("		Envio SYSLOG")

        else:
            #cumplio directiva E

            if debug > 1:
                print("La linea existe y cumplio exclusividad")

            if linea_cfg_cumple.estado!="negada":
                linea_cfg_cumple.estado="validada"
                #print("validada- "+str(linea_cfg_cumple.texto))

                if debug > 1:
                    print("Linea exclusive de config VALIDADA: "+str (linea_cfg_cumple.texto))

            if e_tcg_linea.warning:
                linea_cfg_cumple.warning=True

                if debug > 1:
                    print("Linea marcada como WARNING")

    #for linea_cfg in config.lineas_cfg:
    #	#print(":::: "+linea_cfg.texto+"  estado: "+linea_cfg.estado)

    if debug > 0:
        print("Complete los grupos EXCLUSIVE"+"\n")
        print("######################## PROCESO las lineas del template con semantica independiente (sin grupos) ######")


    ############ Barro lineas de tratamiento independiente (no relacionada G,E, etc) por linea
    ############  esto mejor antes para ya salir si pending o pass

    for linea_tcg in template.lineas_tcg:
        fin=False


        # barro todas las lineas que son de interpretacion independiente por linea
        if not linea_tcg.group and not linea_tcg.exclusive and not linea_tcg.comentario and not fin:

            if debug > 1:
                print("Linea tcg independiente a analizar (sin grupo y que no es comentario):")
                print(str(linea_tcg.patron)+"   directivas:"+str(linea_tcg.directivas))
                #print("Entro una unica vez a exec_directiva con la directiva Principal")

            # # PENDING## esta primera porque pisa resto ##################################
            # deprecada uso (...)?  como PENDING
            # if  linea_tcg.pending  and not fin:
            # 	#print("PENDING")
            # 	# no hago nada es como un comentario
            # 	fin = True


            # PASS ## esta segunda porque tambien se pasa de largo #########
            if linea_tcg.d_pass  and not fin:

                if debug > 1:
                    print("Contiene directiva PASS")

                #print("PASS")
                exec_directiva("P",linea_tcg,config,owner,element,debug)
                fin = True		

            # NEGATE ## esta segunda porque tambien se pasa de largo #########
            if linea_tcg.negate  and not fin:
                #print("NEGATE")

                if debug > 1:
                    print("Contiene directiva NEGATE")

                exec_directiva("N",linea_tcg,config,owner,element,debug)
                fin = True		



            # MANDATORIO ##################################
            if not linea_tcg.optative  and not fin:
                #print("MANDATORIO")

                if debug > 1:
                    print("Es MANDATORIA")

                exec_directiva("M",linea_tcg,config,owner,element,debug)
                fin = True



            
            # OPTATIVO ###################################
            if linea_tcg.optative  and not fin:
                #print("OPTATIVE")

                if debug > 1:
                    print("Es OPTATIVA")

                exec_directiva("O",linea_tcg,config,owner,element,debug)
                fin = True


    #################################################################
    #REPORTE
    #################################################################

    #print("######################### INICIO REPORTE ####################")

    print("")
    print("######################### INICIO REPORTE " + str(element) + "#################################")
    print("")

    #cant_lineas_config = len(config.lineas_cfg)
    cant_lineas_config = 0 #(no vacias)
    cant_lineas_validadas = 0
    cant_lineas_warning = 0
    cant_lineas_pass = 0
    cant_lineas_negadas = 0
    cant_lineas_mandatory_failed = 0
    cant_lineas_pending = 0
    lineas_warning=""
    lineas_validadas=""
    lineas_no_validadas=""
    lineas_pass=""
    lineas_mandatory_failed = ""
    lineas_negadas = ""
    lineas_pending = ""

    #armo info imprimible por grupos y saco totales parciales

    #print(" -------------------------  CONFIGURACION  ------------------------------")
    for l_conf in config.lineas_cfg:
        #print(str(l_conf.texto))

        if l_conf.estado == "negada":
            lineas_negadas=lineas_negadas+"\n"+l_conf.texto
            cant_lineas_negadas+=1

        if l_conf.estado == "validada":
            lineas_validadas=lineas_validadas+"\n"+l_conf.texto
            cant_lineas_validadas+=1

        if l_conf.estado != "validada" and l_conf.texto!="" :
            lineas_no_validadas=lineas_no_validadas+"\n"+l_conf.texto


        if l_conf.warning:
            lineas_warning=lineas_warning+"\n"+l_conf.texto
            cant_lineas_warning+=1

        if l_conf.d_pass:
            lineas_pass=lineas_pass+"\n"+l_conf.texto
            cant_lineas_pass+=1

        if l_conf.texto != "":
            cant_lineas_config += 1

    cant_lineas_no_validadas= cant_lineas_config - int(cant_lineas_validadas)


    if debug > 1:
        print("Lineas del Template TCG (marca en los mandatory_failed):")

    for l_tcg in template.lineas_tcg:

        if debug > 1:
            print(l_tcg.texto)

        if l_tcg.mandatory_failed:

            if debug > 1:
                print("fue mandtory_failes == true")

            lineas_mandatory_failed=lineas_mandatory_failed+"\n"+l_tcg.patron_no_esc+"  "+str(l_tcg.directivas)
            cant_lineas_mandatory_failed+=1

        if l_tcg.pending:

            if debug > 1:
                print("fue pending == true")

            lineas_pending=lineas_pending+"\n"+str(l_tcg.texto)
            cant_lineas_pending+=1

    # genero archivos salid
        # escribo a archivo config que fue validada
        # las lineas que no escriba al hacer la comparacion con el original va a marcarmelas en rojo

    # Configuracion que esta validad (Verde)
    text_file = open(arch_config_validada, "wt")
    for l_conf in lineas_validadas.splitlines():
        n = text_file.write(l_conf+'\n')
    text_file.close()

    # Configuracion que esta no validad (Verde)
    text_file = open(arch_config_no_validada, "wt")
    for l_conf in lineas_no_validadas.splitlines():
        n = text_file.write(l_conf+'\n')
    text_file.close()

    # Configuracion completa + Mandatory Failed(al compara lo que no este en arch anterior va a estra Rojo)
    text_file = open(arch_config, "wt")
    for l_conf in config.lineas_cfg:
        # elimino lineas vacias
        if l_conf.texto != config.CR and l_conf.texto!="":
            n = text_file.write(l_conf.texto+'\n')

    info_mandatory_failed = '''

    -- DIRECTIVAS MANDATORIAS NO CUMPLIDAS EN LA CONFIGURACION --

    '''+str(lineas_mandatory_failed)+'''

    '''

    text_file.write(info_mandatory_failed)
    text_file.close()

    print("-----------------------------Compliance KPI -------------------------------")
    print("")

    cant_total_mandatory=0
    for l_tcg in template.lineas_tcg :
            if not l_tcg.optative and not l_tcg.comentario:
                cant_total_mandatory+=1

    #print(str(cant_lineas_mandatory_failed))
    #print(str(cant_total_mandatory))

    try:
        percent_mandatory_failed = (float(cant_lineas_mandatory_failed) / float(cant_total_mandatory))*100
    except:
        percent_mandatory_failed = 0

    try:
        percent_no_validado = 100-(float(cant_lineas_validadas)/cant_lineas_config)*100
    except:
        percent_no_validado = 100


    print("% Mandatorios no Cumplidos: "+str(round(percent_mandatory_failed, 2))+"%" )
    print("")

    print("% Configuracion no validada: "+str(round(percent_no_validado, 2))+"%" )
    print("")

    #######  inserto en influx ###########################

    # data = [
    #         {
    #             "measurement": "cpu_load_short",
    #             "tags": {
    #                 "host": "server01",
    #                 "region": "us-west"
    #             },
    #             "time": "2009-11-10T23:00:00Z",
    #             "fields": {
    #                 "value": 0.64
    #             }
    #         }
    #     ]



    data = [
        {
            "measurement": "Compliance_integrado",
            "tags": {
                "nodo": str(element),
                "owner": str(owner)
            },
            "time": '{}'.format(datetime.now().strftime('%m/%d/%Y %H:%M:%S')),
            # "time": "2009-11-10T23:00:00Z",
            "fields": {
                "Mandatorios_no_cumplidos_prct": float(round(percent_mandatory_failed, 1)),
                "Configuracion_no_validada_prct" : float(round(percent_no_validado, 1))
                #"value": str(round(percent_mandatory_failed, 2))
            }
        }
    ]


    print(str(data))

    print("inserto en influxdb-------------------------------------")

    try:
        insert_influxdb(data, database=BaseHook.get_connection('influxdb_conn').schema)
        #print(">>>>>>>>>>>>>>>> OK al escribir en influx")
    except:
        #print(">>>>>>>>>>>>>>>> Error al escribir en influx")
        print("Error al escribir en influx")

    #####################################################

    print("-----------------------------Mandatorios NO Cumplidos: "+str(cant_lineas_mandatory_failed)+" -------------------------------")
    print(lineas_mandatory_failed)
    print("")


    print("---------------------------- Lineas NO Validadas: "+str(cant_lineas_no_validadas)+" --------------------------")
    print("")
    if debug > 1:
        print(lineas_no_validadas)
        print("")  
    else:
        print("Incrementar el nivel de debug para ver este detalle")
        print("") 

    print("---------------------------- Lineas Validadas: "+str(cant_lineas_validadas)+" --------------------------")
#    print(lineas_validadas)
    print("")
    if debug > 0:
        print(lineas_validadas)
        print("")  
    else:
        print("Incrementar el nivel de debug para ver este detalle") 
        print("")

    print("---------------------------- Lineas WARNING: "+str(cant_lineas_warning)+"--------------------------")
    print(lineas_warning)
    print("")

    print("---------------------------- Lineas PASS: "+str(cant_lineas_pass)+"--------------------------")
    print(lineas_pass)
    print("")


    print("-----------------------------Directivas PENDIENTES: "+str(cant_lineas_pending)+" -------------------------------")
    print(lineas_pending)
    print("")


    ###  Genero HTML  con Lib de Fernando ##########################
    #arch_config_validada = "config_validada.cfg"
    #arch_config = "config_full.cfg"




    #leo archivo target
    try:
        with open(arch_config_validada) as t:
            target_lines=t.readlines()
    except FileNotFoundError:
            raise FileNotFoundError("Target file path is not correct")
    #leo cada uno de los archivos source

    #leo archivo source
    try:
        with open(arch_config) as s:
            source_lines=s.readlines()
    except FileNotFoundError:
            raise FileNotFoundError("Source file path is not correct")


    # with open(arch_conf) as file_input: 
    # 	conf_data = file_input.readlines()
    # 	for linea_confg in conf_data:
    # 		linea_confg=linea_confg.strip()
            

    #genero html que muestre diferencias entre el source y target
    #/wrap column original 60 o 70 mejor
    diff=difflib.HtmlDiff(wrapcolumn=110).make_file(source_lines, target_lines, "Configuracion "+element, filename)
    #grabo archivo de diferencias html


    try:
        with open(filename, 'w') as html:
            html.write(diff)
    except FileNotFoundError:
        raise FileNotFoundError("Output dir path is not correct: {0}".format(output_dir))


    print("-------------------------------- FIN:" + str(element) + "--------------------------------")

#####################################################################################3
#########                                                                       ######
######################################################################################

    
def f_Variables_Conocidas(**context):

        # element=context['NODO']
        # owner=context['OWNER']
        # wdir=context['WORK_DIR']+"/"+str(owner)+"/"+str(element)
        source_files=context['source_files']

        template_file = context['file_tcg']
        dest_file   = context['file_tcg']+".solved"

#def f_Variables_Conocidas(source_files,dest_file,template_file):

#source_files,w_dir+"/"+nodo+"/"+owner+"_"+nodo+"_template_solved.tcg",w_dir+"/"+nodo+"/"+owner+"_"+nodo+"_template.tcg"

        # genera lista de dict a partir de lista de json (lista_de_variables)
        lista_dict=[]
        for file_var in source_files:
            with open(file_var) as json_file: 
                data_dict = json.load(json_file)
                lista_dict.append(data_dict)


        # genera variable template_configuracion a partir de template_file
        
        try:
            with open(template_file, "r") as text_file:
                template_configuracion = text_file.read()
        except:
            #send_tambo_event("CORE","OP_tecoComplianceOperatorVariablesConocidas","FILE_ACCESS","WARNING","No se pudo acceder a archivo de template: "+str(template_file))
            #logging.error('\n\n:::! Error - No se pudo acceder a archivos de template.')
            print("No puedo realizar open de file: "+template_file)
            return(-1)           

        #--print("sigo en funcion a variables conocidas <--------")
        #--print("template de configuracion:")
        #--print(str(template_configuracion))

        max_prof = 25
        # en realidad aca voy convendria cargar una lista de files json, similar a como esta el flatten

        # genero un unico diccionario a partir de la lista de diccionarios
        z={}
        for x in lista_dict:
            z.update(x)


        # modifico template para que invoque las variables dentro del dict unificado
        template_configuracion_final=""

        # obtengo lista con nombre limpio de variables invocadas en la linea
        for linea in template_configuracion.splitlines():
            linea_final=linea
            matches = re.findall('<<.*?>>', linea)
            for i in range(len(matches)):
                matches[i]=matches[i].replace('<<','').replace('>>','')
                #reemplazo variables por solo el ultimo elemento, para usarlo despues en jinja asi, donde al ir iterando no es necesario invocar cadena completa, solo la ultima
                linea_final= re.sub(matches[i],matches[i].split(".")[-1],linea_final)
                linea_final=linea_final.replace('<<','{{').replace('>>','}}')


            #inicializo preambulo
            preambulo_jinja2=""
            cierre_jinja2=""

            for vx in matches:
                        vx_parsed=vx.split('.')
                        # barro las jerarquias del dict hasta llegar a la referenciada (todo dato es lista)
                        pos=1
                        seg_prev="z"
                        for vx_segment in vx_parsed:
                            #{% for region in z.region %}
                            preambulo_jinja2+="{% for "+str(vx_segment)+" in "+str(seg_prev)+"."+str(vx_segment)+" %}"+"\n"
                            #genero preambulo
                            pos=pos+1
                            seg_prev=vx_segment


            ## deduplica preambulo respetando orden, para eliminar ciclo redundantes


            preambulo_jinja2_final=""
            for lineax in preambulo_jinja2.splitlines():
                if not re.findall(lineax,preambulo_jinja2_final):
                    preambulo_jinja2_final+=lineax+"\n"

            #cierro todos los for que abri
            for xxx in preambulo_jinja2_final.splitlines():
                    cierre_jinja2 += "{% endfor %}"

            # confecciono template final para jinja2
            template_configuracion_final+=preambulo_jinja2_final
            template_configuracion_final+=linea_final
            template_configuracion_final+=cierre_jinja2
            template_configuracion_final+="\n"

        #--print("template jinja2 resultante: \n"+template_configuracion_final)

        #Resuelvo el jina2
        t = Template(template_configuracion_final)
        result = t.render(z=z)

        #elimino lineas en blanco que me quedan del parseo
        result_final=""
        for line in result.splitlines():
            if line != "":
                result_final+=line+"\n"

        # ordeno alfabeticamente para agrupar por elementos de mayor jerarquia, solo por un tema visual
        # la comparacion contra la config debera ser linea a linea 
        #########  este paso lo elimino ya que perjudica performance y no cambia resultado final
        
        # lineas=result_final.splitlines()
        # lineas.sort()
        # result_final=""
        # for l in lineas:
        #     result_final+=l+"\n"

        #--print("configuracion resultante: \n"+result_final)

        output_file = open(dest_file, "w")
        n = output_file.write(result_final)
        output_file.close()

        return result_final



def f_teco_flatten(source_files):

        """
        Esta funcion desjerarquizas un archivo de configuración generando un nueva archivo con dicho contenido
        El archivo generado tendra el mismo nameing del original con agregando _flatten.cgf al final del archivo y reemplazando su extensión original
        PAra mas detalles sobre de desjerarquizacion de configuraciones referirse al operador Teco_Flatten_Config
        
        """

        re_comentario = re.compile(r'^!|^\s+!|^#|^\s#+')
        for file in source_files:
            print("proceso file::::::::: " +str(file))
            nivel=0
            cola_jerarquia=[]
            grupo=[]

            for i in range(1,20):
                grupo.append({"submenu":"vacio","separador":""})


            dest_path = str(file)+".flatten"

            ###################################################


            # Desjerarquizo
            print('::: Preparo archivo de salida:'+ dest_path +'\n')
            f = open(dest_path, "w")
            print('::: Abro archivo de entrada:'+ file +'\n')
            with open(file,errors='replace') as file_input: 

                file_data = file_input.readlines()
                for linea_nl in file_data:
                    linea=linea_nl.rstrip()  ## con rstrip le saco newline sino me la cuenta como \s para el match
                    match_comentario = re_comentario.search(linea)
                    if not match_comentario:
                        # me fijo si ingrese a nuevo submenu y lo registro
                        identacion_anterior = grupo[nivel]["separador"]
                        match_nueva_jerarquia = re.search(rf"^{identacion_anterior}\s+",linea)
                        if match_nueva_jerarquia:
                            nivel+=1
                            grupo[nivel]["separador"]=match_nueva_jerarquia.group()
                            grupo[nivel]["submenu"]=linea_anterior
                        else:
                            # me fijo si baje/sali de jerarquia y a que nivel
                            for iii in range(0,nivel+1):
                                ident = grupo[iii]["separador"]
                                match_out= re.search(rf"^{ident}\S+",linea)
                                if match_out:
                                    nivel=iii
                        # computo jerarquia actual
                        subgrupos=" "
                        for ii in range(1,nivel+1):
                            subgrupos+=grupo[ii]["submenu"]+" "
                        # armo linea flattened
                        linea_flat=subgrupos+linea
                        # homogeinizo espaciado
                        linea_flat = re.sub(r'\s+',' ',linea_flat)
                        linea_flat = re.sub(r'^ ','',linea_flat)
                        f.write(linea_flat+"\n")
                        # paso a siguiente linea
                        linea_anterior=linea
            f.close()
            print(':::Desjerarquizacion Finalizada')


#función para habilitar el código del DAG en Sphinx
def doc_sphinx():
    pass

#############  MAIN ###############################

def TCGComplianceIntegrado(file_tcg,dir_config,file_config,dir_inv,owner,**kwargs):
    #w_dir = "/usr/local/airflow/dags/cel_core/tcg_Compliance_integrado/tcg/output"
    #nodo="MUN1NA"
    #nodo_one="TEST"
    #owner="transporte"

    # for root, dirs, files in os.walk(r'./output'):
    #     print("root:",root)
    #     print("dirs:",dirs)
    #     print("files:",files)


    # array con archivos de inventario
    


    # proceso archivos de inventarios .json para convertir sus componentes en iterables
    # y obtengo una lista de los mismos (es decir decir de lo .json del dir inv )
    source_files_raw = glob.glob(dir_inv + "/*.json")
    print("listado de json::::::::::::::::: "+ str(source_files_raw))
    inv_files = []
    for sf in source_files_raw:
        json_c_list(str(sf),str(sf)+".array")
        inv_files.append(str(sf)+".array")


    # me fijo si se especifica un nodo o debo correr el compliance en todo el directorio del owner

    # if nodo_one!="":
    #     list_nodes_dir=[nodo_one]   
    # else:
    #     list_nodes_dir = os.listdir(w_dir+"/"+owner)
    print("dir config:"+dir_config)
    config_files = glob.glob(dir_config + "/" + file_config )
    print("CONFIG FILES:::::::::::::::"+str(config_files))
    # completo template tcg con variables conocidas
    f_Variables_Conocidas(source_files=inv_files,file_tcg=file_tcg)

    for config_file in config_files:

        print("#################  Proceso: " + str(config_file) + "##############################")
        print("--- Completo Tempalte con variables conocidas:")

#        f_Variables_Conocidas(source_files=inv_files,file_tcg=file_tcg)

        #print("Aca realizaria el flatten de la cpnfig")
        print("---- Aplico la desjerarquizacion de la configuracion:")


        f_teco_flatten([config_file])

        print("Realizo el Compliance de la Configuracion:")
        f_Compliance_Unificado(file_tcg=file_tcg, config_file=config_file, OWNER=owner, DEBUG_LEVEL=3)

        #f_limpio_archivos(OWNER=owner,NODO=nodo,WORK_DIR=w_dir)

            
#tasks
t0 = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

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

def render(equipo, modelo):
    w_dir = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates"
    #w_dir = "/io/cel_core/compliance/afijo/configuraciones"
    conf_file = f"*{equipo}*.config"
    #conf_file = "CISCO_CMT5-ALM1-CBR8bis.config"
    dir_json_inv = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/inv_json/"
    #arch_template = "/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_cmts.tcg"
    arch_template = f"/usr/local/airflow/dags/cel_afijo/tcg_Compliance_integrado/templates/template_{equipo}.tcg"

    #CISCO_sun2mu.config     HUAWEI_gu11mu.config  HUAWEI_sfr3mu.config  JUNIPER_roa1.tor1.config

    tcg = PythonOperator(
        task_id="TCG_Compliance_Integrado_{}".format(equipo),
        python_callable=TCGComplianceIntegrado,
        op_kwargs={"file_tcg": arch_template ,"dir_config" : w_dir, "file_config": conf_file, "dir_inv": dir_json_inv,"owner": "AET"},
        dag=dag
    )
    return t0 >> tcg


modelo='E6000'

equipos = read_mongo(modelo)
for equipo in equipos:
    render(equipo,modelo)

# t0 >> tc1