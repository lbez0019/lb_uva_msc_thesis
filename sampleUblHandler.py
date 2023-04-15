import xml.sax
import subprocess
import os

class UBLHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.current_element = ""
        self.facts = []
        self.fact_values = []
        self.aggregate_component_stack = []
        self.basic_component_stack = []
        self.basic_component_stack_flag = False
        self.parsed_aggregate_components = []
        # self.invoice_number = ""
        # self.invoice_date = ""

    def startElement(self, name, attrs):
        self.current_element = name

    def endElement(self, name):
        if name.startswith("cac"):
            self.current_element = name
        else:
            self.current_element = ""

    def characters(self, content):
        if self.current_element.startswith("cac") and self.current_element not in self.parsed_aggregate_components:
            aggregate_value = self.current_element.split(":")[1]
            if self.aggregate_component_stack and self.aggregate_component_stack[-1] == aggregate_value\
                    and self.basic_component_stack:
                self.basic_component_stack = []
                self.basic_component_stack_flag = False
                self.parsed_aggregate_components.append(self.current_element)
                self.aggregate_component_stack.pop()
            elif not self.basic_component_stack_flag:
                self.basic_component_stack_flag = True
                self.aggregate_component_stack.append(aggregate_value)

        elif self.current_element.startswith("cbc"):
            basic_component_name = self.current_element.split(":")[1]
            if self.basic_component_stack_flag is True:
                self.basic_component_stack.append(basic_component_name)
            fact_value = content
            fact_name = ''

            for name in reversed(self.aggregate_component_stack):
                fact_name += (name + '_')

            fact_name += basic_component_name

            if (fact_value.isdigit() or (fact_value.startswith('-') and fact_value[1:].isdigit())):
                self.facts.append(f'Fact {fact_name} Identified by Int')
            else:
                self.facts.append(f'Fact {fact_name} Identified by String')

            self.fact_values.append(f'+{fact_name}({fact_value})')

        # if self.current_element == "cbc:ID":
        #     self.invoice_number = content
        # elif self.current_element == "cbc:IssueDate":
        #     self.invoice_date = content

def try_parse(parser=None):
    # Construct the path to the XML file
    subdirectory = "files"
    filepathOrder = os.path.join(subdirectory, "example-order.xml")
    filepathInvoice = os.path.join(subdirectory, "example-invoice.xml")
    filepathTest= "example-test.xml"

    try:
        parser.parse(filepathTest)
        parser.parse(filepathOrder)
        parser.parse(filepathInvoice)
    except Exception as ex:
        print(ex)
    else:
        print("OK")

def eflint_communicate():
    # # Run WSL and move up one directory
    # result = subprocess.run(['wsl', 'cd ..', 'ls'], shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # out, err = result.communicate()
    # command = ['wsl', '/home/lukebezzina/.cabal/bin/eflint-repl', 'conditioned-by/jackpot.eflint', ':quit']
    command = ['wsl','/home/lukebezzina/.cabal/bin/eflint-server', 'conditioned-by/jackpot.eflint', '5000', '--debug']
    result = subprocess.run(command, capture_output=True,)
    x = str(result.stdout, 'utf-16')
    print(result.stdout.decode())



parser = xml.sax.make_parser()
handler = UBLHandler()
parser.setContentHandler(handler)
try_parse(parser)
# eflint_communicate()

# print(handler.invoice_number)
# print(handler.invoice_date)
