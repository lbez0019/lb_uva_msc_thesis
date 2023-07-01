import requests
import time
from fact_generator import FactGenerator


class EFLINTCommunicator:
    @staticmethod
    def check_all_enabled_transitions(instance):
        enabled_transitions = {}

        url = 'http://localhost:8080/command'
        myobj = {
            "uuid": instance["data"]["uuid"],
            "request-type": "command",
            "data":
                {
                    "command": "status"
                }
        }

        transitions = requests.post(url, json=myobj).json()["data"]["response"]["all-enabled-transitions"]

        for transition in transitions:
            enabled_transitions[transition["fact-type"]] = transition["textual"]

        return enabled_transitions

    @staticmethod
    def check_transition_enabled(instance, act, actor, recipient):
        actor = actor[0]
        return EFLINTCommunicator.check_transition_validity(instance, act, actor, recipient, "Enabled")

    @staticmethod
    def check_transition_holds(instance, action):
        act = action['Act'][0]
        actor = action['Actor'][0]
        recipient = action['Recipient']

        return EFLINTCommunicator.check_transition_validity(instance, act, actor, recipient, "Holds")

    @staticmethod
    def check_transition_validity(instance, act, actor, recipient, query_op):
        phrase = f"?{query_op}({act}({actor}"
        phrase += f", {', '.join(recipient)}" if recipient else ""
        phrase += f")) Where Holds({actor})"
        if recipient:
            phrase += f" && Holds({recipient[0]})"

        response = EFLINTCommunicator.eflint_server_request(instance, phrase)
        query_result = response["data"]["response"]["query-results"][0]

        return query_result

    @staticmethod
    def create_fact(fact, values, uuid):
        url = "http://localhost:8080/command"
        value_count = sum(isinstance(item, list) for item in values)
        values = [[item[0], f'"{item[1]}"'] if isinstance(item[1], str) else item for item in values]
        payload = FactGenerator.define_fact_payload(value_count, uuid, fact, values)

        while True:
            try:
                response = requests.post(url, payload)
                if response.status_code == 200:
                    errors = response.json()["data"]["response"]["errors"]
                    if errors:
                        print("Error during fact creation:", errors[0])
                        return 0
                    return 1
                print("Error. Response Status Code:", response.status_code)
                return 0

            except requests.exceptions.RequestException as e:
                print("Request Error:", e)
                return 0
            except Exception:
                print(f"eFLINT instance instantiating...")
            time.sleep(0.5)

    @staticmethod
    def create_instance():
        url = "http://localhost:8080/upload"
        file_path = './policies/policies.eflint'  # Replace with the path to your file

        try:
            with open(file_path, 'rb') as file:
                files = {'fileToUpload': file}
                response = requests.post(url, files=files)

                if response.status_code == 200:
                    return response.json()
                else:
                    return None
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
        except Exception as e:
            print(e)

    @staticmethod
    def eflint_initiate(eflint_facts, eflint_fact_values):
        # write_eflint_template(eflint_facts)
        EFLINTCommunicator.web_server_check()
        instance_created = EFLINTCommunicator.create_instance()

        if instance_created is not None:
            for key, value in eflint_fact_values.items():
                for individual_values in value:
                    EFLINTCommunicator.create_fact(key, individual_values, instance_created['data']['uuid'])
        else:
            print("Instance not created! Facts were not added to environment.")

        print(f'Facts created in eFLINT instance: {instance_created["data"]["uuid"]}')
        return instance_created

    @staticmethod
    def eflint_server_request(instance, phrase):
        url = 'http://localhost:8080/command'
        object = {
            "uuid": instance["data"]["uuid"],
            "request-type": "command",
            "data":
                {
                    "command": "phrase",
                    "text": phrase
                }
        }

        return requests.post(url, json=object).json()

    @staticmethod
    def trigger_transition(instance, act, actor, recipient):
        phrase = f"+({act}({actor[0]}"
        phrase += f", {', '.join(recipient)}" if recipient else ""
        phrase += f")) Where Holds({actor[0]})"
        if recipient:
            phrase += f" && Holds({recipient[0]})"

        return EFLINTCommunicator.eflint_server_request(instance, phrase)

    @staticmethod
    def write_eflint_template(fact_types):
        with open('./policies/policies.eflint', 'w') as f:
            for fact_type in fact_types:
                f.write(f"{fact_type}\n")

    @staticmethod
    def web_server_check():
        url = "http://localhost:8080/get_all"

        # Retry every 1s until web server is OK
        while True:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    print("eFLINT Server OK")
                    return True
            except requests.exceptions.RequestException as e:
                print("Error:", e)
            time.sleep(1)

    @staticmethod
    def kill_instance(instance):
        url = 'http://localhost:8080/command'
        object = {
            "uuid": instance["data"]["uuid"],
            "request-type": "command",
            "data":
                {
                    "command": "kill"
                }
        }

        return requests.post(url, json=object).json()
