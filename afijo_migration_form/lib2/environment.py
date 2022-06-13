import os

def get_env() -> dict:
    """Metodo que devuelve un diccionarion con el nombre del entorno y su ip donde esta corriendo el DAG.
        el nombre sale de la variable de entorno $FA_ENTORNO 
        (se puede verificar entrando al docker de airflow y hacer un 'echo $FA_ENTORNO')
        
        Salidas posibles:  
         
         data = {"name_env" : "fa-dev", 
                 "ip_env": "10.247.2.44"}
         
         data = {"name_env" : "fa-test", 
                 "ip_env": "10.247.2.43"}
         
         data = {"name_env" : "fa-prod", 
                 "ip_env": "10.247.2.42"}
    """
    # Get the list of user's environment variables
    env_var = dict(os.environ).get("FA_ENTORNO")
    # Print the list of user's environment variables
    # print(f'Environment variable: {env_var}')
    
    data = {
        "name_env" : env_var,
        "ip_env": ""
    }

    if env_var == "fa-dev":
        data["ip_env"] = "10.247.2.44"  
    elif env_var == "fa-test":
        data["ip_env"] = "10.247.2.43"  
    elif env_var == "fa-prod":
        data["ip_env"] = "10.247.2.42" 
    else:
        data["ip_env"] = None
        
    return data 