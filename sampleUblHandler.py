import xml.sax
import subprocess
import os


class UBLHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.document_name, self.current_element = "", ""
        self.basic_element_add_flag = False
        self.aggregate_component_stack, self.fact_values, self.parsed_aggregate_components = [], [], []
        self.facts = set()
        self.composite_components = {}

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
            self.document_name = self.current_element

        # Aggregate (composite) component parsed
        elif self.current_element.startswith("cac") and self.current_element not in self.parsed_aggregate_components:
            value = self.current_element.split(":")[1]

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

                # Adding composite component to dict, or adding new list to its values if already parsed
                if val not in self.composite_components:
                    self.composite_components.update({val: []})
                self.composite_components[val].append([])

        # Element is a leaf UBL node
        elif self.current_element.startswith("cbc"):
            self.basic_element_add_flag = True  # Status - adding leaf UBL nodes
            fact_value = content
            fact_name = self.current_element.split(":")[1]

            # Individual Fact Type declarations
            if is_float_digit(fact_value) or (fact_value.startswith('-') and is_float_digit(fact_value[1:])):
                self.facts.add(f'Fact {fact_name} Identified by Int')
            else:
                self.facts.add(f'Fact {fact_name} Identified by String')

            # If element is a child of an aggregate (composite) component
            if not len(self.aggregate_component_stack) == 0:
                val = self.aggregate_component_stack[0]
                for i in range(1, len(self.aggregate_component_stack)):
                    val += ('_' + self.aggregate_component_stack[i])
                # adding fact and fact type to composite_components dictionary
                self.composite_components[val][-1].append([fact_name, fact_value])

            else:
                self.fact_values.append(f'+{fact_name}({fact_value})')


# Check if value is a decimal value (negative, positive) or not
def is_float_digit(n: str) -> bool:
    return n.replace('.', '', 1).isdigit()


def try_parse(file):
    # Construct the path to the XML file
    parser = xml.sax.make_parser()
    document_handler = UBLHandler()
    parser.setContentHandler(document_handler)
    composite_facts = set()
    composite_fact_values = []

    try:
        parser.parse(file)

        facts = list(document_handler.facts)
        composite_fact_creation(document_handler, composite_facts, composite_fact_values)
        composite_facts_list = list(composite_facts)
        facts.sort()
        composite_facts_list.sort()

        # Extending fact types and facts with composite instances
        facts.extend(composite_facts_list)
        document_handler.fact_values.extend(composite_fact_values)

    except Exception as ex:
        print(ex)
    else:
        print("OK")


def composite_fact_creation(document_handler, composite_facts, composite_fact_values):
    for parsed_fact in document_handler.composite_components:
        for item in document_handler.composite_components[parsed_fact]:
            if not len(item) == 0:
                fact_value = f'+{parsed_fact}('
                fact = f'Fact {parsed_fact} Identified by '

                for item_property in item:
                    fact += f' {item_property[0]} *'
                    fact_value += f' {item_property[1]},'

                if fact[-1] == '*':
                    fact = fact[:-1]
                    fact_value = fact_value[:-1]
                fact_value += ')'

                composite_facts.add(fact)
                composite_fact_values.append(fact_value)


def eflint_communicate(document, eflint_facts, eflint_fact_values):
    # # Run WSL and move up one directory
    # result = subprocess.run(['wsl', 'cd ..', 'ls'], shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # out, err = result.communicate()
    # command = ['wsl', '/home/lukebezzina/.cabal/bin/eflint-repl', 'conditioned-by/jackpot.eflint', ':quit']
    command = ['wsl', '/home/lukebezzina/.cabal/bin/eflint-server', 'conditioned-by/jackpot.eflint', '5000', '--debug']
    result = subprocess.run(command, capture_output=True, )
    x = str(result.stdout, 'utf-16')
    print(result.stdout.decode())


subdirectory = "documents"
for filename in os.listdir(subdirectory):
    f = os.path.join(subdirectory, filename)
    if os.path.isfile(f):
        try_parse(f)
