import xml.sax

import inflect


class UBLHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.document_name, self.current_element = "", ""
        self.basic_element_add_flag = False
        self.aggregate_component_stack, self.parsed_aggregate_components, self.parsed_documents = [], [], []
        self.facts = set()
        self.composite_components, self.fact_values = {}, {}

    def reset_values(self):
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
            p = inflect.engine()
            self.parsed_documents.append(self.current_element.lower())
            self.document_name = self.current_element.lower()
            document_count = self.parsed_documents.count(self.current_element.lower())
            if document_count > 1:
                self.document_name += f"_{p.number_to_words(document_count)}"
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
                self.fact_values[fact_name] = [[[fact_name, fact_value]]]
