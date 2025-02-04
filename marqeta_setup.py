from faker import Faker
from marqeta import Client
import re
import json
import random
import os
import secrets
import requests as r
from sdk.ext import PeerTransfer, Authorization
import random

'''
HIERARCHY

BUSINESS_TOKEN
    DEPT_TOKEN1
        AH_GROUP_TOKEN1
            EMPLOYEE_TOKEN1
            EMPLOYEE_TOKEN2
            EMPLOYEE_TOKEN3
    DEPT_TOKEN2
        AH_GROUP_TOKEN2
            EMPLOYEE_TOKEN1
            EMPLOYEE_TOKEN2
            EMPLOYEE_TOKEN3
'''

'''
Each user will have their own MarqetaClient instance.
'''


class MarqetaClient:
    def __init__(self):
        # Fake data generator
        self.fake = Faker()

        # Marqeta Client
        client_payload = {
            'base_url': "https://sandbox-api.marqeta.com/v3/",
            'application_token': os.getenv('MY_APP'),
            'access_token': os.getenv('MY_ACCESS'),
            'timeout': 60
        }
        self.client_sdk = Client(client_payload['base_url'], client_payload['application_token'],
                                 client_payload['access_token'], client_payload['timeout'])

        # Constants
        self.DEPARTMENT_LIST = ['IT', 'AC', 'MK', 'HR', 'PD', 'RD',
                                'SC',
                                'LG']
        self.READABLE_DEPARTMENTS = {'IT': 'IT', 'AC': 'ACCOUNTING', 'MK': 'MARKETING', 'HR': 'HUMAN RESOURCES',
                                     'PD': 'PRODUCTION', 'RD': 'RESEARCH & DEVELOPMENT', 'SC': 'SECURITY',
                                     'LG': 'LOGISTICS'}

        self.DEPARTMENT_TOKEN_TO_OBJECTS = {}

        self.CURRENT_DEPT = None

        self.MANAGERS = {}

        self.GENDERS = ['FEMALE', 'MALE']

        for i, dept in enumerate(self.DEPARTMENT_LIST):
            m_gender = random.choice(self.GENDERS)
            f_name = ''
            l_name = ''
            email = ''
            if m_gender == 'MALE':
                f_name = self.fake.first_name_male()
                l_name = self.fake.last_name_male()
            else:
                f_name = self.fake.first_name_female()
                l_name = self.fake.last_name_female()
            self.MANAGERS[dept] = {
                'first_name': f_name,
                'last_name': l_name,
                'gender': m_gender,
                'email': dept + '@eay.com', 'pass': 'root', 'manager_dept_FK': i + 1
            }

        self.BUSINESS_NAME = 'Einberg & Ying LLP'
        self.BUSINESS_TOKEN = ''.join(
            re.findall('([A-Z])', self.BUSINESS_NAME)) + '_' + secrets.token_urlsafe(5)[0:8] + '_'

        self.TOKEN_COUNTER = 0
        self.DEPT_TOKEN_COUNTER = 0
        self.AH_GROUP_TOKEN_COUNTER = 0
        self.EMPLOYEE_TOKEN_COUNTER = 0

        self.FUNDING_PAYLOAD = {'name': self.BUSINESS_NAME + ' Program Funding',
                                'active': True,
                                'token': self.BUSINESS_TOKEN + '_FUNDING'
                                }

        self.BUSINESS_PAYLOAD = {'token': self.BUSINESS_TOKEN,
                                 'business_name_dba': self.BUSINESS_NAME,
                                 'general_business_description': self.fake.catch_phrase()
                                 }

        self.funding_source = []
        self.business = []
        self.departments = []
        self.ah_groups = []
        self.employees = []
        self.transactions = []
        self.department_employees = {}

        self.setup()
        print('\n\nMARQETA SETUP DONE\n\n')

    '''
    Initialize class attributes of MarqetaClient.
    '''

    def setup(self):
        self.funding_source = self.create_program_funding_source(
            self.FUNDING_PAYLOAD)

        self.business = self.create_business(self.BUSINESS_PAYLOAD)

        master_fund_amount = float(random.randint(1_500_000, 10_000_000))
        self.fund(master_fund_amount, gpa_type='business',
                  fund_source_token=self.funding_source.token, dest_token=self.business.token)

        self.departments = [self.create_department(
            dept) for dept in self.DEPARTMENT_LIST]

        self.DEPARTMENT_TOKEN_TO_OBJECTS = dict(zip(self.DEPARTMENT_LIST, self.departments))

        amount_per_department = master_fund_amount / (len(self.departments) * 3)

        adjusted_percents = self.generate_percents()

        for i, dep in enumerate(self.departments):
            self.transactions.append(self.transfer(
                amount_per_department * adjusted_percents[i], self.business.token, dep.token))

        self.ah_groups = [self.create_ah_group(
            dept) for dept in self.DEPARTMENT_LIST]

        for i, dept in enumerate(self.departments):
            self.generate_employee_data(
                12, self.departments[i].token, self.ah_groups[i].token)

        # print(json.dumps(self.department_employees,indent=4))

    # HIERARCHY
    # CREATE PROGRAM FUNDING SOURCE

    '''
    Used to create a program funding source.

    fund - the request fields needed to create a program funding source.
    '''

    def create_program_funding_source(self, fund):
        return self.client_sdk.funding_sources.program.create(fund)

    '''
    Used to create a single business.

    business - the request fields needed to create a business.
    '''

    def create_business(self, business):
        return self.client_sdk.businesses.create(business)

    def generate_percents(self):
        rs = []
        s = 0
        for i in range(len(self.DEPARTMENT_LIST)):
            r = random.random()
            s += r
            rs.append(r)

        return [i / s for i in rs]

    '''
    Used to fund the main business account.

    amount: float - the amount to transfer.

    gpa_type: str - the type of the GPA account to fund (business or user).

    fund_source_token: str - the business/user token to transfer from.

    dest_token: str - the business/user token to transfer to.

    currency_code: str - the currency type.
    '''

    def fund(self, amount: float, gpa_type: str, fund_source_token: str, dest_token: str, currency_code: str = 'USD'):
        payload = {'token': self.BUSINESS_TOKEN + '_GPA_TOKEN',
                   gpa_type + '_token': dest_token,
                   'funding_source_token': fund_source_token,
                   'amount': amount,
                   'currency_code': currency_code
                   }
        return self.client_sdk.gpa_orders.create(payload)

    '''
    Used to make transfers from one GPA account to another.

    amount: float - the amount to transfer.

    token: str - the unique identifier of the peer transfer.

    source_token: str - the business/user token to transfer from.

    dest_token_is_user: bool - defaults to False, assuming b2b/d2d transfer.

    dest_token: str - the business/user token to transfer to.

    currency_code: str - the currency type.
    '''

    def transfer(self, amount: float, source_token: str, dest_token: str, dest_token_is_user: bool = False,
                 token: str = None, currency_code: str = 'USD'):

        payload = {
            'sender_business_token': source_token,
            'currency_code': currency_code,
            'amount': str(amount)
        }

        if dest_token_is_user:
            payload['recipient_user_token'] = dest_token
        else:
            payload['recipient_business_token'] = dest_token

        if token:
            payload['token'] = token

        payload = json.dumps(payload)

        headers = {
            'Content-type': 'application/json',
        }

        return PeerTransfer(json.loads(r.post('https://sandbox-api.marqeta.com/v3/peertransfers', headers=headers,
                                              data=payload,
                                              auth=(os.getenv('MY_APP'), os.getenv('MY_ACCESS'))).content))

    def retrieve_balance(self, token):
        return self.client_sdk.balances.find_for_user_or_business(token)

    # CREATE DEPARTMENT USERS (BUSINESSES)
    '''
    Used to create departments (businesses).

    department - the request fields to create a business.
    '''

    def create_department(self, department):
        dept_payload = {'token': self.BUSINESS_TOKEN + '_' + department + str(self.DEPT_TOKEN_COUNTER),
                        'business_name_dba': department
                        }
        # print(f'dept_payload: {dept_payload}')
        self.DEPT_TOKEN_COUNTER += 1
        return self.client_sdk.businesses.create(dept_payload)

    # CREATE ACCOUNT HOLDER GROUPS FOR EACH DEPARTMENT
    # WITH APPROPRIATE CONFIG
    '''
    Used to create account holder groups.

    department - the request fields to create an account holder group.
    '''

    def create_ah_group(self, department):
        ah_group_payload = {
            'token': self.BUSINESS_TOKEN + '_AH_GROUP' + str(self.AH_GROUP_TOKEN_COUNTER),
            'name': self.BUSINESS_TOKEN + '_AH_GROUP'
        }
        # print(f'ah_group_payload: {ah_group_payload}')
        self.AH_GROUP_TOKEN_COUNTER += 1
        return self.client_sdk.account_holder_groups.create(ah_group_payload)

        # CREATE USERS OF EACH DEPARTMENT WITH PARENT BEING THE DEPARTMENT USER TOKEN AND HAVING ACH TOKEN

    '''
    Used to create a user.

    employee - the request fields to create a user.
    '''

    def create_employee(self, employee):
        return self.client_sdk.users.create(employee)

    '''
    Used to generate user data.

    n: int - the amount of employees to generate per department.

    parent_token: str - the parent token of the user.

    ah_group_token: str - the account group holder token of the user.
    '''

    def generate_employee_data(self, n: int, parent_token: str, ah_group_token: str):

        for count in range(n):
            e_payload = {
                "token": self.BUSINESS_TOKEN + '_e' + str(self.EMPLOYEE_TOKEN_COUNTER),
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "parent_token": parent_token,
                "account_holder_group_token": ah_group_token
            }
            card_payload = {
                'user_token': e_payload['token'],
                'card_product_token': os.getenv('SAM_CARD_PRODUCT_TOKEN')
            }
            self.EMPLOYEE_TOKEN_COUNTER += 1

            e_object = self.create_employee(e_payload)
            self.employees.append(e_object)

            if parent_token in self.department_employees:

                self.department_employees[parent_token].append(e_object.token)
            else:

                self.department_employees[parent_token] = [e_object.token]

            card = self.client_sdk.cards.create(card_payload)

    # EXPORT BUSINESS DATA AS JSON OR JUST SUBMIT DIRECTLY TO MARQETA API

    '''
    Print all businesses.

    clt - print a specific business.
    '''

    def print_businesses(self, clt=None):

        def v(i: str):
            print(json.dumps(json.loads(i), indent=4))
            token = json.loads(i)['token']
            if len(token) < 9:
                print(token)

        v(clt.__str__()) if clt is not None else [
            v(u.__str__()) for u in self.client_sdk.businesses.stream()]

    '''
    Print all clients.

    clt - print a specific client.
    '''

    def print_clients(self, clt=None):

        def v(i: str):
            print(json.dumps(json.loads(i), indent=4))
            # token = json.loads(i)['token']
            # print(client.balances.find_for_user_or_business(token))

        # If you provide a client, it'll print the info, otherwise print all clients

        v(clt.__str__()) if clt is not None else [
            v(u.__str__()) for u in self.client_sdk.users.stream()]

    '''
    Print all account holder groups.

    clt - print a specific account holder group.
    '''

    def print_ah_groups(self, clt=None):

        def v(i: str):
            print(json.dumps(json.loads(i), indent=4))
            # token = json.loads(i)['token']
            # print(client.balances.find_for_user_or_business(token))

        # If you provide a client, it'll print the info, otherwise print all clients

        v(clt.__str__()) if clt is not None else [
            v(u.__str__()) for u in self.client_sdk.account_holder_groups.stream()]

    # def print_hierarchy(self):


# ESTABLISH THE DEPARTMENTS AS CONSTANTS/ACCOUNT HOLDER GROUPS


# FOR EACH DEPARTMENT/ACCOUNT HOLDER GROUP, CREATE A RANDOM AMOUNT OF USERS FOR EACH GROUP WHOSE PARENTS ARE THE BUSINESS
if __name__ == '__main__':
    pass
    # client = MarqetaClient()
