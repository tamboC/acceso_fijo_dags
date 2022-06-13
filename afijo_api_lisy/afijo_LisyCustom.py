"""
    Documentar codigo con Docstring
    Path de este directorio /usr/local/airflow/dags/cel_afijo
    Path de la carpeta Ansible /urs/local/ansible/
"""
import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
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
    default_args=default_args
)
    
LISY_AMBIENTE = 'PROD'

class LisyHook():
    # """
    # Hook to interact with the API.
    # """
    
    # def __init__(self, *args, **kwargs):
    def __init__(self, LISY_AMBIENTE):
        # """
        #  Interactua con Datapower y con la API-Rest de Lisy.
        
        # Se deben crear las siguientes conexiones:
        # Ambiente TEST (default): Lisy_DP_TEST, Lisy_api_TEST
        # Ambiente UAT: Lisy_DP_UAT, Lisy_api_UAT
        # Ambiente PRODUCCION: Lisy_DP_PROD, Lisy_api_PROD

        # En funcion de la variable airflow "LISY_AMBIENTE" (TEST | UAT | PROD), se elegira el ambiente contra el que interactúa el hook. Default: 'TEST'

        # """

        self.ambiente = LISY_AMBIENTE
        if self.ambiente == 'TEST' or self.ambiente is None:
            self.ambiente = 'TEST'
            self.conn_token='Lisy_DP_TEST'
            self.conn_api='Lisy_api_TEST'
            self.lisy_token_usr='LisyFullConsumer'
            self.lisy_token_pwd='Teco2020_'
            self.lisy_token_host='sesiont.personal.com.ar'
            self.lisy_api_host='apit.telecom.com.ar'
        elif self.ambiente == 'UAT':
            self.conn_token='Lisy_DP_UAT'
            self.conn_api='Lisy_api_UAT'
            self.lisy_token_usr='b348c0c8e3626351923b049a8ee08cda'
            self.lisy_token_pwd='ad3c676c3639768a432af82f4e978910937ef4fbd24b374e160dc39282870259'
            self.lisy_token_host='sesionu.personal.com.ar'
            self.lisy_api_host='apiu.telecom.com.ar'
        elif self.ambiente == 'PROD':
            self.conn_token='Lisy_DP_PROD'
            self.conn_api='Lisy_api_PROD'
            self.lisy_token_usr='5820d511c405d17f318c56e17dd717d8'
            self.lisy_token_pwd='aefd54c578d60b2b835200770d2b9bed74a235df17849a33bc48f3a7cce15f78'
            self.lisy_token_host='sesion.personal.com.ar'
            self.lisy_api_host='api.telecom.com.ar'

        self.__lisy_init()
        
        # try: #carga dos conexiones.
        #     #una para conseguir un token entregado por 'datapower'
        #     #otra para acceder con el token a la api
        #     # connection_token = BaseHook.get_connection(self.conn_token)
        #     # connection_api = BaseHook.get_connection(self.conn_api)

        # except:
        #     #self.conn_id='lisy_default'
        #     #connection = BaseHook.get_connection(self.conn_id)
        #     self.log.error (f'Error en la lectura de los datos de las conexiones: {self.conn_token} o {self.conn_api}')


        #Requiere crear objeto 'Connection' en Airflow
        #self.password = connection_token.password
        # self.lisy_token_pwd=connection_token.password
        # self.lisy_token_usr=connection_token.login
        # self.lisy_token_pwd='Teco2020_'
        # self.lisy_token_usr='LisyFullConsumer'
        # self.lisy_token_pwd='ad3c676c3639768a432af82f4e978910937ef4fbd24b374e160dc39282870259'
        # self.lisy_token_usr='b348c0c8e3626351923b049a8ee08cda'

        #self.lisy_conn_port=connection.port
        # self.lisy_token_host='sesionu.personal.com.ar'
        
        # self.lisy_api_host='apiu.telecom.com.ar'


    def get_request(self, token, endpoint, tipo, body=None):
        """

        Esta funcion ejecuta el query en Lisy (condis).
        Necesita un token self.token
        
        Args:
            token: el token recibido en el pedido de 'get_token
            tipo: GET, POST
            endpoint: el endpoint de la api rest de Lisy
            body (opcional): si el request lleva body, este argumento lleva el contenido del body.
        Returns:
        
        """

        """
        MODIFICAR PARA AGREGAR BODY
        import requests

        url = "https://dlcondisdb18:27443/web/condisrest/port/"

        payload="{\r\n    \"identifier\": {\r\n        \"shelfName\": \"IC1.HOR1\",\r\n        \"portInterfaceName\": \"9/0/1\"\r\n    }\r\n}"
        headers = {
        'Authorization': 'Bearer c9371d7466977261cc3fa4ad25f7bf31',
        'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        print(response.text)
 
        {
            "identifier": {
                "shelfName": "IC1.HOR1",
                "portInterfaceName": "9/0/1"
            }
        }
        """

        self.token = token
                
        # url = 'https://{0}:443/proxyrest/lisy/web/condisrest/{1}'.format(self.lisy_api_host,endpoint)
        url = 'https://{0}:443/proxyrest/lisy/web/condisrest/{1}'.format(self.lisy_api_host,endpoint)
        #print (':::::URL::::',url)
        
        # self.log.info (f'::: API CONTENT: get_request {url}')
        # self.log.info (f'::: API CONTENT: get_request.body {body}')
        # self.log.debug (f'::: TOKEN : {self.token}')
        print(f'::: API CONTENT: get_request {url}')
        print(f'::: API CONTENT: get_request.body {body}')
        print(f'::: TOKEN : {self.token}')
        #print ('========= TOKEN ======', self.token)
        
        if body is None:
            payload = {}
        else:
            payload = body
        
        headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {0}'.format(self.token),
        'Cookie':'TS016d2cf6=0154ce2499fd2dd02f2c91cebc97efe857db1c7f91b61612598f800f9710a96f951fcca02cdbe66bc12bff1a7f9dc9e62d2d3f0d16'
        }

        try:
            return requests.request(tipo, url, headers=headers, data = payload)
            #return requests.request(tipo, url, headers=headers, data = payload, verify= False)
            #return r.json()
        except:
            self.log.error ('ERROR EN LA QUERY::: QUERY INEXISTENTE')

    
    def chk_token(self):
        """
        este metodo devuelve la estructura full del token, para que se pueda imprimir en pantalla
        """
        return (self.get_token(full=True)) 
    

    def get_token(self,full=False):

        """

        Esta funcion obtiene el token entregado por Datapower, dadas las credenciales que se recuperan de las conexiones creadas, y leídas en __init__()
        
        Args: 
            full = True | False (default)
            
                True: asigna a self.token el valor del access_token recibido desde datapower, y devuelve la estructura completa de la respuesta de datapower.
                
                False: asigna a self.token el valor del access_token recibido desde datapower.
        Returns:
            Estructura recibida de datapower, si full=True.
        
        """
        # print("ACA")
        Auth_b64 = base64.b64encode((self.lisy_token_usr + ':' + self.lisy_token_pwd).encode('ascii'))
        Auth_b64 = 'Basic ' + str(Auth_b64,'utf-8') #convierto a string porque base64 devuelve binario

        url = "https://{0}/openam/oauth2/realms/root/realms/authappext/access_token?grant_type=client_credentials".format(self.lisy_token_host)
        payload = {}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            #'Authorization': 'Basic TGlzeUZ1bGxDb25zdW1lcjpUZWNvMjAyMF8=',
            'Authorization': Auth_b64,
            'Cookie':
            'TS01f6b324=0154ce24993a13345c3f2c0ede41c6e79fbfd8aac34f61f79203d0250287f8c16a61a5d513a445490eb21302540a7d39eb16d6ac3f'
            }       


        #url = "https://{0}:{1}/web/condisrest/accessTokens".format(self.lisy_conn_host, self.lisy_conn_port)
        #payload = "{\"user\": \"%(user)s\",\"password\": \"%(pwd)s\"}"%{'user': self.lisy_conn_usr, 'pwd': self.lisy_conn_pwd}
        #headers = {'Content-Type': 'application/json'}
        #self.log.info (f'::: API CONTENT: get_token {url}')
        print(f'::: API CONTENT: get_token {url}')
        print(f'::: API CONTENT: Usuario {self.lisy_token_usr}')
        print(f'::: API CONTENT: Password {self.lisy_token_pwd}')
        #r = requests.request("POST", url, headers=headers, data = payload, verify= False)
        r = requests.request("POST", url, headers=headers, data = payload)
        print(r.status_code)
        if r.status_code == 401:
            print(f'!::: Error en las credenciales de acceso a Datapower, con el usuario << {self.lisy_token_usr} >>.')
            print(f'Respuesta recibida: {r._content}, con status_code = {r.status_code}')
            # self.log.error (f'!::: Error en las credenciales de acceso a Datapower, con el usuario << {self.lisy_token_usr} >>.')
            # self.log.error (f'Respuesta recibida: {r._content}, con status_code = {r.status_code}')
            raise ValueError('Authentication failed.')
        elif r.status_code == 405:
            # self.log.error (f'!::: Error en las credenciales de acceso a Datapower, con el usuario << {self.lisy_token_usr} >>.')
            # self.log.error (f'Respuesta recibida: {r._content}, con status_code = {r.status_code}')
            print(f'!::: Error en las credenciales de acceso a Datapower, con el usuario << {self.lisy_token_usr} >>.')
            print(f'Respuesta recibida: {r._content}, con status_code = {r.status_code}')
            raise ValueError('Authentication failed.')
        if r.status_code != 200:
            # self.log.error (f'!::: Error en la solicitud del Token con el usuario {self.lisy_token_usr}.')
            # self.log.error (f'Respuesta recibida: {r._content}, con status_code = {r.status_code}')
            print(f'!::: Error en la solicitud del Token con el usuario {self.lisy_token_usr}.')
            print(f'Respuesta recibida: {r._content}, con status_code = {r.status_code}')
            self.token = '9999999999-GET-ERROR-9999999999'
        else:
            #Por pedido de Seguridad Informatica, uso "id_token" en lugar de "access_token"
            #self.token = r.json()['access_token']
            self.token = r.json()['id_token']
            #print(r.json()['id_token'])
            if (full): return r.json() #devuelve la estructura full del token
            return (self.token)

    def __lisy_init(self):
        print(f'\n')
        print(f'****** Inicializando Lisy API para el ambiente {self.ambiente} ******')
        print(f'\n')

def doc_sphinx():
    pass

def operadorLisyQueryCustom():
    api = LisyHook(LISY_AMBIENTE)
    tk_data = api.chk_token()
    print(f"El token es: ", tk_data['access_token'])
   
    body_id = ['*','','']
    body_dict = {
                    "parameters": body_id
                }

    query = 'OcupacionRedHFC-VistaFisica'
    endpoint_query = 'queries/{0}.json'.format(query)
    get_dat = api.get_request(token = tk_data['access_token'], endpoint = endpoint_query, tipo = 'POST' , body=json.dumps(body_dict))
    with open('resultado_api_{}.json'.format(query), 'w') as f:
        json.dump(get_dat.json(), f, ensure_ascii=False, indent=4)


#tasks

t1 = PythonOperator(
    task_id='Operador_Lisy_Query_Custom',
    python_callable= operadorLisyQueryCustom,
    dag=dag
)

t0 = DummyOperator(task_id='dummy_task', retries=1, dag=dag)

t0 >> t1