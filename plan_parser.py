import xml.sax
import subprocess
import os
import requests
import time
import traceback
import inflect
from act_parser import Executor, ActionParser


class UBLHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.document_name, self.current_element = "", ""
        self.basic_element_add_flag = False
        self.aggregate_component_stack, self.parsed_aggregate_components = [], []
        self.facts = set()
        self.composite_components, self.fact_values = {}, {}

    # Triggered every time an opening XML Element is parsed
    def startElement(self, name, attrs):
        self.current_element = name
        # Resetting parsed CAC elements, multiple instances of same CAC are possible
        self.parsed_aggregate_components = []

    # Triggered every time a closing XML Element is parsed
    def endElement(self, name):
        if name.startswith("cac"):
            self.current_element = name
        else:
            self.current_element = ""

    def characters(self, content):
        # First Element in UBL == Document Name
        if self.document_name == "":
            self.document_name = self.current_element.lower()
            self.fact_values["documents_added"] = [[["documents_added", self.document_name]]]

        # Aggregate (composite) component parsed
        elif self.current_element.startswith("cac") and self.current_element not in self.parsed_aggregate_components:
            value = (self.current_element.split(":")[1]).lower()

            # End Element for composite component parsed
            if self.aggregate_component_stack and self.basic_element_add_flag \
                    and self.aggregate_component_stack[-1] == value:
                self.parsed_aggregate_components.append(self.current_element)
                self.aggregate_component_stack.pop()

            # Start Element for composite component parsed
            elif not self.aggregate_component_stack or self.aggregate_component_stack[-1] != value:
                self.basic_element_add_flag = False  # Status - adding aggregate (composite) nodes
                val = ''

                if not len(self.aggregate_component_stack) == 0:
                    for name in self.aggregate_component_stack:
                        val += (name + '_')

                self.aggregate_component_stack.append(value)
                val += value
                val = f'{self.document_name}_{val.lower()}'

                # Adding composite component to dict, or adding new list to its values if already parsed
                if val not in self.composite_components:
                    self.composite_components.update({val: []})
                self.composite_components[val].append([])

        # Element is a leaf UBL node
        elif self.current_element.startswith("cbc"):
            self.basic_element_add_flag = True  # Status - adding leaf UBL nodes
            fact_value = content
            fact_name = f'{self.document_name}_{(self.current_element.split(":")[1]).lower()}'

            # Individual Fact Type declarations
            # if fact_value.isdigit() or (fact_value.startswith('-') and fact_value[1:].isdigit()):
            if fact_value.isdigit():
                self.facts.add(f'Fact {fact_name} Identified by Int.')
                fact_value = int(fact_value)
            else:
                self.facts.add(f'Fact {fact_name} Identified by String.')

            # If element is a child of an aggregate (composite) component
            if not len(self.aggregate_component_stack) == 0:
                val = (self.aggregate_component_stack[0]).lower()
                for i in range(1, len(self.aggregate_component_stack)):
                    val += ('_' + self.aggregate_component_stack[i])
                val = f'{self.document_name}_{val}'
                # adding fact and fact type to composite_components dictionary
                self.composite_components[val][-1].append([fact_name, fact_value])

            else:
                # self.fact_values.append(f'+{fact_name}({fact_value}).')
                self.fact_values[fact_name] = [[[fact_name, fact_value]]]


def write_eflint_template(fact_types):
    with open('../../eflint-server/web-server/test.eflint', 'w') as f:
        for fact_type in fact_types:
            f.write(f"{fact_type}\n")


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


def define_fact_payload(value_count, uuid, fact, fact_values):
    if value_count == 1:
        return f'{{ "uuid": "{uuid}", "request-type": "command", "data":	{{ "command": "create", "value": {{' \
               f'"fact-type" : "{fact}", "value" : {fact_values[0][1]} }} }} }}'
    else:
        sub_values = ""
        for item in fact_values:
            sub_values += f'{{ "fact-type" : "{item[0]}", "value" : {item[1]} }},'
        sub_values = sub_values[:-1]
        return f'{{ "uuid": "{uuid}", "request-type": "command", "data":	{{ "command": "create", "value": {{' \
               f'"fact-type" : "{fact}", "value" : [{sub_values}] }} }} }}'


def create_fact(fact, values, uuid):
    url = "http://localhost:8080/command"
    value_count = sum(isinstance(item, list) for item in values)
    values = [[item[0], f'"{item[1]}"'] if isinstance(item[1], str) else item for item in values]
    payload = define_fact_payload(value_count, uuid, fact, values)

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
        except Exception as e:
            print(f"Error: {e}, eFLINT instance still instantiating.")
        time.sleep(0.5)


def composite_fact_creation(document_handler, composite_facts, composite_fact_values):
    for fact in document_handler.composite_components:
        parsed_fact = fact.lower()
        composite_fact_values[parsed_fact] = []

        for item in document_handler.composite_components[parsed_fact]:
            composite_fact_values[parsed_fact].append([])
            item.sort()
            if not len(item) == 0:
                fact = f'Fact {parsed_fact} Identified by '
                for item_property in item:
                    fact += f' {item_property[0]} *'
                    composite_fact_values[parsed_fact][-1].append([item_property[0], item_property[1]])

                if fact[-1] == '*':
                    fact = fact[:-1] + '.'

                composite_facts.add(fact)


def create_instance():
    url = "http://localhost:8080/create"
    payload = '{ "template-name": "test.eflint", "flint-search-paths": []}'

    try:
        response = requests.post(url, payload)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def eflint_initiate(eflint_facts, eflint_fact_values):
    command = ['wsl', 'bash', '-c', 'cd /mnt/c/Users/lukeb/Documents/Education/MSc_Software_Engineering/Thesis'
                                    '/Project/eflint-server/web-server && mvn exec:java -Dexec.mainClass="eflint.Main"']

    # Run eflint server in the background
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # write_eflint_template(eflint_facts)
    web_server_status = web_server_check()
    instance_created = create_instance()

    if instance_created is not None:
        for key, value in eflint_fact_values.items():
            for individual_values in value:
                create_fact(key, individual_values, instance_created['data']['uuid'])
    else:
        print("Instance not created! Facts were not added to environment.")

    print(f'Facts created in eFLINT instance: {instance_created["data"]["uuid"]}')
    return instance_created


def retrieve_all_scenarios(executor, action_parser):
    action_list = action_parser.retrieve_action_list()
    scenarios = executor.retrieve_scenarios(action_list)

    return scenarios


def check_enabled_transitions(instance):
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


def try_parse(file):
    parser = xml.sax.make_parser()
    document_handler = UBLHandler()
    parser.setContentHandler(document_handler)
    composite_facts = set()
    composite_fact_values = {}

    try:
        parser.parse(file)

        facts = sorted(document_handler.facts)
        composite_fact_creation(document_handler, composite_facts, composite_fact_values)

        facts.extend(sorted(composite_facts))
        document_handler.fact_values.update(composite_fact_values)

        return facts, document_handler.fact_values

    except Exception:
        print(traceback.format_exc())


def update_with_merge(current_dict, new_dict):
    for key, value in new_dict.items():
        if key in current_dict:
            current_dict[key] += value
        else:
            current_dict[key] = value
    return current_dict


def eflint_terminate():
    command = ['wsl', 'bash', '-c', 'kill $(lsof -t -i:8080)']
    subprocess.run(command, capture_output=True)


def check_valid_scenarios(instance, executor, action_parser):
    valid_scenarios = []
    incomplete_scenarios = []
    all_scenarios = retrieve_all_scenarios(executor, action_parser)

    for scenario in all_scenarios:
        valid_bool = True
        violating_transition = ""
        for transition in scenario:
            enabled_transitions = check_enabled_transitions(instance)

            if transition in enabled_transitions:
                response = eflint_server_request(instance, enabled_transitions[transition])
                output_events = response["data"]["response"]["output-events"]
                violations = response["data"]["response"]["violations"]

                if not (output_events and not violations):
                    violating_transition = transition
                    valid_bool = False
                    break
            else:
                violating_transition = transition
                valid_bool = False
                break

        if valid_bool:
            valid_scenarios.append(scenario)
        else:
            incomplete_scenarios.append([scenario, violating_transition])

    return valid_scenarios, incomplete_scenarios

def provide_alternative_action(incomplete_scenario, instance, action_parser):
    scenario, violated_action = incomplete_scenario
    p = inflect.engine()

    for transition in scenario:
        enabled_transitions = check_enabled_transitions(instance)

        if transition == violated_action:
            action = action_parser.actions[transition]
            if check_transition_holds(instance, action):
                print(f"Action {transition} holds. Permuting pre-conditions until transition is enabled.")
                original_precondition = action["Conditioned by"][0]
                precondition_permutations = action_parser.derive_alternative_preconditions(original_precondition)

                for i in range(1, len(precondition_permutations)):
                    precondition = precondition_permutations[i]
                    number_string = p.number_to_words(i)
                    alt_name = f'{transition}_alt{number_string}'
                    try_alternative_actions(instance, action, precondition, alt_name)
                    trigger_transition(instance, alt_name, action["Actor"], action["Recipient"])
                    result = check_transition_enabled(instance, alt_name, action["Actor"], action["Recipient"])

                    if result == "success":
                        difference = [x for x, y in zip(precondition, original_precondition.split(' ')) if x != y]
                        return f"Successful Transition: {alt_name} \nValid Precondition: {precondition}"
                return f"None of the permuted pre-conditions helped in enabling {transition}."
            else:
                result = f"Action {transition} does not hold. Make sure that values for Actor: {action['Actor']}"
                result += f", Recipient: {action['Recipient']}" if action["Recipient"] else ""
                result += " are provided in the UBL plans submitted."
                return result

        if transition in enabled_transitions:
            eflint_server_request(instance, enabled_transitions[transition])


def try_alternative_actions(instance, action, permuted_precondition, alt_name):
    temp_action = action.copy()
    temp_action["Act"][0] = alt_name
    temp_action["Conditioned by"] = [' '.join(permuted_precondition)]
    executable_action = ' '.join(f'{key} {" ".join(values)}' for key, values in temp_action.items() if values)

    return eflint_server_request(instance, executable_action)


def check_transition_validity(instance, act, actor, recipient, query_op):
    phrase = f"?{query_op}({act}({actor}"
    phrase += f", {', '.join(recipient)}" if recipient else ""
    phrase += f")) Where Holds({actor})"
    if recipient:
        phrase += f" && Holds({recipient[0]})"

    response = eflint_server_request(instance, phrase)
    query_result = response["data"]["response"]["query-results"][0]

    return query_result


def trigger_transition(instance, act, actor, recipient):
    phrase = f"+({act}({actor[0]}"
    phrase += f", {', '.join(recipient)}" if recipient else ""
    phrase += f")) Where Holds({actor[0]})"
    if recipient:
        phrase += f" && Holds({recipient[0]})"

    return eflint_server_request(instance, phrase)


def check_transition_enabled(instance, act, actor, recipient):
    actor = actor[0]
    return check_transition_validity(instance, act, actor, recipient, "Enabled")


def check_transition_holds(instance, action):
    act = action['Act'][0]
    actor = action['Actor'][0]
    recipient = action['Recipient']

    return check_transition_validity(instance, act, actor, recipient, "Holds")


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


executor = Executor()
action_parser = ActionParser()

subdirectory = "business_documents"
facts = ['Fact documents_added Identified by String.']
fact_values = {}
for filename in os.listdir(subdirectory):
    f = os.path.join(subdirectory, filename)
    if os.path.isfile(f):
        new_facts, new_fact_values = try_parse(f)
        facts.extend(new_facts)
        fact_values = update_with_merge(fact_values, new_fact_values)
        # fact_values.update(new_fact_values)

instance_created = eflint_initiate(facts, fact_values)
valid_scenarios, incomplete_scenarios = check_valid_scenarios(instance_created, executor, action_parser)

for valid_scenario in valid_scenarios:
    print(f"Valid Scenario: {valid_scenario}\n")

for i in range(len(incomplete_scenarios)):
    scenario, violated_action = incomplete_scenarios[i]
    print(f"Incomplete Scenario: {scenario}")
    print(f"Violated Action: {violated_action}\n")
    alternative_action = provide_alternative_action(incomplete_scenarios[i], instance_created, action_parser)
    print(alternative_action)

eflint_terminate()
