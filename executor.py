import os
import traceback
import xml.sax

from action_parser import ActionParser
from dag_builder import DAGBuilder
from eflint_communicator import EFLINTCommunicator
from fact_generator import FactGenerator
from scenario_handler import ScenarioHandler
from ubl_parser import UBLHandler
from utils import Utils


class Executor:
    @staticmethod
    def check_if_valid_scenario_exists(valid_scenarios):
        # Does a valid scenario exist? (i.e. containing only all actions defined)
        for valid_scenario in valid_scenarios:
            if Utils.has_same_elements(valid_scenario, selected_options):
                DAGBuilder.display_valid_scenario(graph, selected_options)
                print(f"\nScenario is valid! Valid Scenario: {valid_scenario}")
                return True
        return False

    @staticmethod
    def check_if_invalid_scenario_exists(invalid_scenarios, invalid_scenarios_summarised):
        # Does an invalid scenario exist? (i.e. containing only all actions defined)
        for invalid_scenarios_summarised in invalid_scenarios_summarised:
            if Utils.has_same_elements(invalid_scenarios_summarised, selected_options):
                print(f"\nInvalid Scenario: {invalid_scenarios_summarised}")
                user_input = input("Would you like to go about an alternative scenario? \n"
                                   "Please enter 'yes' or 'no' (default: yes): ") or "yes"

                if user_input != "yes":
                    DAGBuilder.display_invalid_scenario(graph, selected_options)
                    selected_similar_scenario = invalid_scenarios_summarised
                    for invalid_scenario in invalid_scenarios:
                        if invalid_scenario[0] == selected_similar_scenario:
                            ScenarioHandler.invoke_alternative_action(action_parser, instance_created, invalid_scenario)
                            return True
                return False
        return False


    @staticmethod
    def define_facts():
        subdirectory = "plans"
        facts = ['Fact documents_added Identified by String.']
        fact_values = {}
        for filename in os.listdir(subdirectory):
            f = os.path.join(subdirectory, filename)
            if os.path.isfile(f):
                new_facts, new_fact_values = Executor.parse_plans(f)
                facts.extend(new_facts)
                fact_values = Utils.update_with_merge(fact_values, new_fact_values)

        return EFLINTCommunicator.eflint_initiate(facts, fact_values)

    @staticmethod
    def parse_plans(file):
        parser = xml.sax.make_parser()
        document_handler = UBLHandler()
        parser.setContentHandler(document_handler)
        composite_facts = set()
        composite_fact_values = {}

        try:
            parser.parse(file)
            facts = sorted(document_handler.facts)
            FactGenerator.composite_fact_creation(document_handler, composite_facts, composite_fact_values)
            facts.extend(sorted(composite_facts))
            document_handler.fact_values.update(composite_fact_values)

            return facts, document_handler.fact_values

        except Exception:
            print(traceback.format_exc())


action_parser = ActionParser()

instance_created = Executor.define_facts()
action_list = action_parser.retrieve_action_list()
selected_options = ScenarioHandler.predefined_action_selection(action_list)

print("\nSelected Actions:")
print(','.join(map(str, selected_options)))

valid_scenarios, invalid_scenarios, invalid_scenarios_summarised, graph = \
    ScenarioHandler.categorise_all_scenarios_with_graph(instance_created, action_list)

valid_scenario_chosen = Executor.check_if_valid_scenario_exists(valid_scenarios)
invalid_scenario_chosen = Executor.check_if_invalid_scenario_exists(invalid_scenarios, invalid_scenarios_summarised)

# Incomplete Scenario is chosen
# If invalid scenario is subsequently chosen -> go about it and permute preconditions up until action is enabled
if not (valid_scenario_chosen or invalid_scenario_chosen):
    similar_scenarios = []
    for valid_scenario in valid_scenarios:
        score = Utils.compute_jaccard_similarity(selected_options, valid_scenario)
        similar_scenarios.append([valid_scenario, "Valid", score])

    for invalid_scenario in invalid_scenarios_summarised:
        score = Utils.compute_jaccard_similarity(selected_options, invalid_scenario)
        similar_scenarios.append([invalid_scenario, "Invalid", score])

    print("\nScenario is incomplete. Closest scenarios to the specified one:")
    # sort the list based on the third element in descending order,
    # while considering the second element to prioritize True values over False
    similar_scenarios = sorted(similar_scenarios, key=lambda x: (-x[2], x[1]))

    for i, scenario in enumerate(similar_scenarios):
        print(f"{i + 1}. {scenario}")

    # Get user input
    user_input = input("\nChoose the data scenario you would like to go about: ")
    ScenarioHandler.process_scenario_choice(action_parser, instance_created, user_input,
                                            action_list, similar_scenarios, invalid_scenarios, graph)

EFLINTCommunicator.kill_instance(instance_created)
