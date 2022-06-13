import json
from datetime import datetime

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from teco_ansible.operators.tecoAnsibleOperator_2 import tecoCallAnsible2

@dag(schedule_interval=None, start_date=datetime(2021, 1, 1), catchup=False, tags=['REF'])
def afijo_ref_taskflow_api():
    """
    ### TaskFlow API Tutorial Documentation
    This is a simple ETL data pipeline example which demonstrates the use of
    the TaskFlow API using three simple tasks for Extract, Transform, and Load.
    Documentation that goes along with the Airflow TaskFlow API tutorial is
    located
    [here](https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html)
    """
    @task()
    def extract():
        """
        #### Extract task
        A simple Extract task to get data ready for the rest of the data
        pipeline. In this case, getting data is simulated by reading from a
        hardcoded JSON string.
        """
        data_string = '{"1001": 301.27, "1002": 433.21, "1003": 502.22}'

        order_data_dict = json.loads(data_string)
        return order_data_dict

    @task(multiple_outputs=True)
    def transform(order_data_dict: dict):
        """
        #### Transform task
        A simple Transform task which takes in the collection of order data and
        computes the total order value.
        """
        total_order_value = 0

        for value in order_data_dict.values():
            total_order_value += value

        return {"total_order_value": total_order_value}

    @task()
    def load(total_order_value: float):
        """
        #### Load task
        A simple Load task which takes in the result of the Transform task and
        instead of saving it to end user review, just prints it out.
        """
        print(f"Total order value is: {total_order_value:.2f}")

        context = get_current_context()
        print(context)
        data =context["dag_run"].conf.get("data")
        print(data)

        valor = {'ShelfNetworkRole' : 'FTTH ACCESS', 'PrePro' : "True", 'Vendor' : "Huawei"}
        print(valor)

        #defino mi operador de ansible
        _test_operador_ansible = tecoCallAnsible2(
            task_id='TestOperadorAnsible', 
            pbook_dir='/usr/local/airflow/dags/cel_afijo/ejemplos/ansible',
            playbook='afijo_backupolt_hw_2.yaml',
            connection='credenciales_olt_hw',
            mock=False,
            FILTRO_CUSTOM=valor,
            dict_extravars={"equipo_a":{"mi_key": "mi_valor"},
                            "equipo_b":{{"mi_key": "mi_valor"}}})

        #Ejecuto el operador de ansible
        print("ejecuto operador con variables")

        _test_operador_ansible.execute()
    
    order_data = extract()
    order_summary = transform(order_data)
    load(order_summary["total_order_value"])





tutorial_etl_dag = afijo_ref_taskflow_api()