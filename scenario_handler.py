import inflect
import re

from dag_builder import DAGBuilder
from eflint_communicator import EFLINTCommunicator
from utils import Utils


class ScenarioHandler:
    @staticmethod
    def categorise_all_scenarios_with_graph(instance, action_list):
        valid_scenarios = []
        invalid_scenarios = []
        dependency_graph, all_scenarios = ScenarioHandler.retrieve_all_scenarios(action_list)

        for scenario in all_scenarios:
            valid_bool = True
            violating_transition = ""
            for transition in scenario:
                enabled_transitions = EFLINTCommunicator.check_all_enabled_transitions(instance)

                if transition in enabled_transitions:
                    response = EFLINTCommunicator.eflint_server_request(instance, enabled_transitions[transition])
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
                invalid_scenarios.append([scenario, violating_transition])

        return valid_scenarios, invalid_scenarios, dependency_graph

    @staticmethod
    def retrieve_all_scenarios(action_list):
        items = {}
        for dict_item in action_list:
            act = dict_item['Act'][0]
            creates = dict_item['Creates'].copy()
            creates = Utils.trim_values_end(creates)
            creates = Utils.split_string_until_open_parenthesis(creates)
            items[act] = {'Act': act, 'Creates': creates}

        dag_builder = DAGBuilder()
        dependency_graph = dag_builder.build_dependency_graph(items)

        scenarios = ScenarioHandler.topological_sort(dependency_graph)

        return dependency_graph, scenarios

    @staticmethod
    def explain_precondition_violation(string):
        equality_operators = ['==', '!=', '<', '>', '<=', '>=']
        contains_operators = False

        for operator in equality_operators:
            if operator in string:
                contains_operators = True

                # Escape the equality operators for regex pattern
                escaped_operators = [re.escape(op) for op in equality_operators]
                pattern = '|'.join(escaped_operators)
                sides = re.split(pattern, string)

                left_side = sides[0].strip("()")
                right_side = sides[1].strip("()")
                print(
                    f"- Make sure that \033[1m{left_side}\033[0m is"
                    f" \033[1m{operator}\033[0m than/to \033[1m{right_side}\033[0m")
                break

        if not contains_operators:
            if "Not" in string:
                _, _, substring = string.partition("Not")
                substring = substring.strip("()")
                if "documents_added" in substring:
                    substring = substring.replace("documents_added(", "")
                    print (
                        f"- Document \033[1m{substring}\033[0m should not be submitted. "
                        f"Remove \033[1m{substring}\033[0m from the UBL files added."
                    )
                else:
                    print(
                        f"- Item \033[1m{substring}\033[0m should not hold. "
                        f"Remove instantiation of fact by deleting the respective "
                        f"value for \033[1m{substring}\033[0m from the UBL files added."
                    )
            else:
                string = string.strip("()")
                if "documents_added" in string:
                    string = string.replace("documents_added(", "")
                    print (
                        f"- Document \033[1m{string}\033[0m should be submitted. "
                        f"Make sure to add \033[1m{string}\033[0m to the UBL files submitted."
                    )
                else:
                    print(
                        f"- Item \033[1m{string}\033[0m should hold. "
                        f"Make sure that you add the required values for "
                        f"fact \033[1m{string}\033[0m in the UBL files added, and that the value satisfies the condition.")

    @staticmethod
    def process_scenario_choice(action_parser, instance_created, user_input, action_list, similar_scenarios, invalid_scenarios, graph):
        choice = user_input.strip()
        if choice.isnumeric() and int(choice) <= len(action_list):
            scenario = similar_scenarios[int(choice) - 1]
            selected_similar_scenario = scenario[0]
            if scenario[1] == "Valid":
                DAGBuilder.display_valid_scenario(graph, scenario[0])
                print(f"\nScenario chosen ({selected_similar_scenario}), is valid!")
            else:
                for invalid_scenario in invalid_scenarios:
                    if invalid_scenario[0] == selected_similar_scenario:
                        DAGBuilder.display_invalid_scenario(graph, invalid_scenario)
                        ScenarioHandler.invoke_alternative_action(action_parser, instance_created, invalid_scenario)

    @staticmethod
    def provide_alternative_action(incomplete_scenario, instance, action_parser):
        scenario, violated_action = incomplete_scenario
        p = inflect.engine()

        for transition in scenario:
            enabled_transitions = EFLINTCommunicator.check_all_enabled_transitions(instance)

            if transition == violated_action:
                action = action_parser.actions[transition]
                if EFLINTCommunicator.check_transition_holds(instance, action):
                    print(f"Action {transition} holds. Permuting pre-conditions until transition is enabled.")
                    original_precondition = action["Conditioned by"][0]
                    precondition_permutations = action_parser.derive_alternative_preconditions(original_precondition)

                    for i in range(1, len(precondition_permutations)):
                        precondition = precondition_permutations[i]
                        precondition_string = action_parser.rpn_to_infix(precondition)
                        number_string = p.number_to_words(i)
                        alt_name = f'{transition}_alt_{number_string}'
                        ScenarioHandler.try_alternative_actions(instance, action, precondition_string, alt_name)
                        EFLINTCommunicator.trigger_transition(instance, alt_name, action["Actor"], action["Recipient"])
                        result = EFLINTCommunicator.\
                            check_transition_enabled(instance, alt_name, action["Actor"], action["Recipient"])

                        if result == "success":
                            difference = [y for x, y in zip(precondition, original_precondition.split(' ')) if x != y]
                            print(f"\nSuccessful Transition: {alt_name} ")
                            print(f"Precondition term(s) originally causing a violation: {difference}\n")
                            for violating_precondition in difference:
                                ScenarioHandler.explain_precondition_violation(violating_precondition)
                            return f"\nValid Precondition: {precondition_string}"
                    return f"None of the permuted pre-conditions helped in enabling {transition}."

                else:
                    result = f"Action {transition} does not hold. Make sure that values for Actor: {action['Actor']}"
                    result += f", Recipient: {action['Recipient']}" if action["Recipient"] else ""
                    result += " are provided in the UBL plans submitted."
                    return result

            if transition in enabled_transitions:
                EFLINTCommunicator.eflint_server_request(instance, enabled_transitions[transition])

    @staticmethod
    def predefined_action_selection(action_list):
        # Display the options
        print("\nActions parsed. Select action(s) to be triggered within simulation environment:")
        for i, action in enumerate(action_list):
            print(f"{i + 1}. {action['Act'][0]}")

        user_input = input("\nEnter the numbers of the selected actions for scenario (comma-separated): ")

        # Process the input
        selected_options = []
        user_choices = user_input.split(',')

        for choice in user_choices:
            choice = choice.strip()
            if choice.isnumeric() and int(choice) <= len(action_list):
                selected_options.append(action_list[int(choice) - 1]['Act'][0])

        return selected_options

    # TODO: Move to scenario_handler.py
    @staticmethod
    def topological_sort(dependency_graph):
        # Perform topological sorting to generate valid scenarios
        scenarios = []

        # Find all nodes without incoming edges (sources)
        sources = [node for node in dependency_graph.nodes if dependency_graph.in_degree(node) == 0]

        # Generate scenarios starting from each source node
        for source in sources:
            stack = [(source, [source])]
            action_stack = []

            while stack:
                action_path = []
                if action_stack:
                    init_act, action_path = action_stack.pop()
                node, path = stack.pop()

                successors = list(dependency_graph.successors(node))

                if successors:
                    for successor in successors:
                        action = DAGBuilder.get_action_from_edge(dependency_graph, node, successor)

                        new_action_path = action_path + [action]
                        new_path = path + [successor]
                        action_stack.append((action, new_action_path))
                        stack.append((successor, new_path))
                else:
                    scenarios.append(action_path)

        return scenarios

    @staticmethod
    def try_alternative_actions(instance, action, permuted_precondition, alt_name):
        temp_action = action.copy()
        temp_action["Act"][0] = alt_name
        temp_action["Conditioned by"] = [permuted_precondition]
        executable_action = ' '.join(f'{key} {",".join(values)}' for key, values in temp_action.items() if values)

        return EFLINTCommunicator.eflint_server_request(instance, executable_action)

    @staticmethod
    def invoke_alternative_action(action_parser, instance_created, invalid_scenario):
        scenario, violated_action = invalid_scenario
        print(f"Invalid Scenario: {scenario}")
        print(f"Violated Action: {violated_action}\n")
        print(ScenarioHandler.provide_alternative_action(invalid_scenario, instance_created, action_parser))
