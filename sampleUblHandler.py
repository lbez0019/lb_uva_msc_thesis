import xml.sax
import subprocess
import os

class UBLHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.document_name = ""
        self.current_element = ""
        self.basic_element_add_flag = False
        self.aggregate_component_stack = []
        self.fact_values = []
        self.parsed_aggregate_components = []
        self.facts = set()

    def startElement(self, name, attrs):
        self.current_element = name
        # Resetting parsed CAC elements, multiple instances of same CAC are possible
        self.parsed_aggregate_components = []

    def endElement(self, name):
        if name.startswith("cac"):
            self.current_element = name
        else:
            self.current_element = ""

    def characters(self, content):
        # First Element in UBL == Document Name
        if self.document_name == "":
            self.document_name = self.current_element

        elif self.current_element.startswith("cac") and self.current_element not in self.parsed_aggregate_components:
            value = self.current_element.split(":")[1]

            if self.aggregate_component_stack and self.aggregate_component_stack[-1] == value \
                    and self.basic_element_add_flag:
                self.parsed_aggregate_components.append(self.current_element)
                self.aggregate_component_stack.pop()

            elif not self.aggregate_component_stack or self.aggregate_component_stack[-1] != value:
                self.basic_element_add_flag = False
                self.aggregate_component_stack.append(value)

        elif self.current_element.startswith("cbc"):
            value = self.current_element.split(":")[1]

            self.basic_element_add_flag = True
            fact_value = content
            fact_name = ''

            for name in self.aggregate_component_stack:
                fact_name += (name + '_')
            fact_name += value

            if fact_value.isdigit() or (fact_value.startswith('-') and fact_value[1:].isdigit()):
                self.facts.add(f'Fact {fact_name} Identified by Int')
            else:
                self.facts.add(f'Fact {fact_name} Identified by String')

            self.fact_values.append(f'+{fact_name}({fact_value})')


def try_parse(file):
    # Construct the path to the XML file
    parser = xml.sax.make_parser()
    document_handler = UBLHandler()
    parser.setContentHandler(document_handler)

    try:
        parser.parse(file)

        print(document_handler.document_name)
        print(document_handler.facts)
        print(document_handler.fact_values)

        # eflint_communicate(document_handler.document_name, document_handler.facts, document_handler.fact_values)

    except Exception as ex:
        print(ex)
    else:
        print("OK")


def eflint_communicate(document, eflint_facts, eflint_fact_values):
    # # Run WSL and move up one directory
    # result = subprocess.run(['wsl', 'cd ..', 'ls'], shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # out, err = result.communicate()
    # command = ['wsl', '/home/lukebezzina/.cabal/bin/eflint-repl', 'conditioned-by/jackpot.eflint', ':quit']
    command = ['wsl','/home/lukebezzina/.cabal/bin/eflint-server', 'conditioned-by/jackpot.eflint', '5000', '--debug']
    result = subprocess.run(command, capture_output=True,)
    x = str(result.stdout, 'utf-16')
    print(result.stdout.decode())


subdirectory = "documents"
for filename in os.listdir(subdirectory):
    f = os.path.join(subdirectory, filename)
    if os.path.isfile(f):
        try_parse(f)


