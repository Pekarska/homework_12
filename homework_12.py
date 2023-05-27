import json
from collections import UserDict
from datetime import datetime
import re
from json import JSONDecodeError


class Field:
    pass


class NameField(Field):
    def __init__(self, name: str):
        super().__init__()
        self.value = name

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, new_value):
        if self.__validate_name__(new_value):
            self.__value = new_value

    @staticmethod
    def __validate_name__(new_value):
        if new_value is None:
            raise ValueError('Name cannot be None')
        if str(new_value).strip() == '':
            raise ValueError('Name cannot be empty or whitespaces')
        return True


class PhoneField(Field):
    def __init__(self, phone: str):
        super().__init__()
        self.value = phone

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, new_value):
        if self.__validate_phone__(new_value):
            self.__value = new_value

    def get_phone_code(self):
        return str(self.value).lstrip('+').lstrip('0')

    @staticmethod
    def __validate_phone__(value):
        if value is None:
            raise ValueError('Phone cannot be None')
        if str(value).strip() == '':
            raise ValueError('Phone cannot be empty or whitespaces')
        if re.match(r"^\+?[\d]{10,14}$", value):
            return True
        raise ValueError('Phone is not correct')


class BirthDayField(Field):
    def __init__(self, b: str):
        super().__init__()
        self.date = None
        self.value = b

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, new_value):
        if self.__validate_birthday__(new_value):
            self.__value = new_value

    def __validate_birthday__(self, value):
        if value is None:
            raise ValueError('Birthday cannot be None')
        if str(value).strip() == '':
            raise ValueError('Birthday cannot be empty or whitespaces')
        if re.match(r"^\d{4}\-\d?\d\-\d?\d$", value):
            self.date = datetime.fromisoformat(value)
            if self.date > datetime.now():
                raise ValueError('Birthday cannot be than now')
            return True
        raise ValueError('Birthday is not correct, should be YYYY-MM-DD')

    def get_datetime(self):
        return self.date


class Record:
    name: NameField
    birthday: BirthDayField = None

    def __init__(self, name: str, b: BirthDayField = None):
        self.name = NameField(name)
        self.phones = []
        if b is not None:
            self.birthday = b

    def add_phone(self, phone: PhoneField):
        self.phones.append(phone)

    def edit_phone(self, new_phone: PhoneField):
        self.phones.clear()
        self.add_phone(new_phone)

    def delete_phone(self, number: str):
        phone_code = number.lstrip('+').lstrip('0')
        for s in self.phones:
            if s.get_phone_code() == phone_code:
                self.phones.remove(s)
                break

    def days_to_birthday(self):
        now = datetime.now()
        bd = self.birthday.get_datetime()

        delta1 = datetime(now.year, bd.month, bd.day)
        delta2 = datetime(now.year + 1, bd.month, bd.day)

        return ((delta1 if delta1 > now else delta2) - now).days

    def __str__(self):
        result = self.name.value + '\t| ' + ', '.join(x.value for x in self.phones)
        if self.birthday is not None:
            result += '\t| ' + self.birthday.value + '\t| next birthday in ' + str(self.days_to_birthday()) + ' days'
        return result + '\n'

    def get_json_data(self):
        result = {'name': self.name.value}
        if self.birthday:
            result['birthday'] = self.birthday.value
        result['phones'] = []
        for phone in self.phones:
            result['phones'].append(phone.value)
        return result


class AddressBook:
    def __init__(self, max_page: int = None):
        self.data = {}
        if max_page is None:
            max_page = 3
        self.max_page = max_page

    def add_record(self, r: Record):
        self.data[r.name.value] = r

    def __iter__(self):
        page = []
        for name, record in self.items():
            page.append(record)
            if len(page) == self.max_page:
                yield page
                page = []
        if page:
            yield page

    def __getitem__(self, page_number: int):
        p = 1
        for page in self:
            if page_number == p:
                return page
            p += 1
        raise KeyError('index out of range in book, max page: ' + str(p))

    def find_by_name(self, n: str, use_any=False):
        result = []
        for name, record in self.data.items():
            if use_any and n.lower() in name.lower():
                result.append(record)
            elif not use_any and name.lower() == n.lower():
                result.append(record)
        return result

    def find_by_phone(self, number: str, use_any=False):
        result = []
        for _, record in self.data.items():
            for p in record.phones:
                if use_any and number.lower() in p.value.lower():
                    result.append(record)
                    break
                elif not use_any and number.lower() == p.value.lower():
                    result.append(record)
                    break
        return result

    def items(self):
        return self.data.items()

    def save_to_file(self, filename):
        address_book_json = []
        for _, record in self.data.items():
            address_book_json.append(record.get_json_data())
        with open(filename, "w+") as fh:
            json.dump(address_book_json, fh)

    def load_from_file(self, filename):
        with open(filename, "r+") as fh:
            try:
                address_book_json = json.load(fh)
            except JSONDecodeError as e:
                return str(e)
        self.data = {}
        record_index = 0
        for json_record in address_book_json:
            try:
                if 'name' in json_record:
                    record = Record(json_record['name'])
                    if 'birthday' in json_record:
                        record.birthday = BirthDayField(json_record['birthday'])
                    if 'phones' in json_record:
                        for phone in json_record['phones']:
                            record.add_phone(PhoneField(phone))
                    self.add_record(record)
            except ValueError as e:
                return 'Validation error in ' + str(record_index) + ' record: ' + str(e)


def input_error(func):
    def inner(command, *inputs):
        if command == 'add':
            if inputs and len(inputs) > 1:
                return func(*inputs)
            else:
                return 'Give me name and phone please, birthday optional'
        if command == 'change':
            if inputs and len(inputs) == 2:
                return func(*inputs)
            else:
                return 'Give me name and phone please'
        if command == 'birthday':
            if inputs and len(inputs) == 2:
                return func(*inputs)
            else:
                return 'Give me name and birthday please'
        if command == 'phone':
            if inputs and len(inputs) == 1:
                return func(*inputs)
            else:
                return 'Enter user name'
        if command == 'hello':
            if len(inputs) > 0:
                return func(inputs[0])
            return func(None)
        if command == 'show':
            if inputs and len(inputs) == 1:
                return func(*inputs)
            else:
                return 'Show must be with parameter `all` or name'
        if command == 'find':
            if inputs and len(inputs) == 1:
                return func(*inputs)
            else:
                return 'Find must be with one parameter (part of phone or name)'

        return 'Not correct validation'

    return inner


book = AddressBook()


@input_error
def hello(n):
    if n is None:
        return "How can I help you?"
    else:
        return "Hello " + n + ", how can I help you?"


@input_error
def adding(name, phone, b=None):
    try:
        record = Record(name)
        record.add_phone(PhoneField(phone))
        if b:
            record.birthday = BirthDayField(b)
        book.add_record(record)
        return 'add completed'
    except Exception as e:
        return str(e)


@input_error
def change(n, p):
    try:
        items = book.find_by_name(n)
        if len(items) == 0:
            return 'Name is not found'
        for record in items:
            phone = PhoneField(p)
            record.edit_phone(phone)
        return 'Number is changed'
    except Exception as e:
        return str(e)


@input_error
def show(n):
    info_line = ''
    if n == 'all':
        p = 1
        for page in book:
            info_line += '====\tpage: ' + str(p) + '\t====\n'
            for record in page:
                info_line += str(record)
            p += 1
    else:
        try:
            page_number = int(n, 10)
            if page_number < 1:
                page_number = 1
            for record in book[page_number]:
                info_line += str(record)
        except KeyError as e:
            return str(e)
        except ValueError:
            items = book.find_by_name(n)
            if len(items) == 0:
                return 'Name is not found'
            for record in items:
                info_line += str(record)
    return info_line


@input_error
def find(n):
    items = book.find_by_name(n, use_any=True)
    if len(items) == 0:
        items = book.find_by_phone(n, use_any=True)
    if len(items) == 0:
        return 'Not found record by ' + str(n)
    info_line = ''
    for record in items:
        info_line += str(record)
    return info_line


@input_error
def birthday(n, b):
    for record in book.find_by_name(n):
        try:
            b = BirthDayField(b)
            record.birthday = b
            return 'Birthday set successfully'
        except Exception as e:
            return str(e)
    return 'Name is not found'


commands = {
    'hello': hello,
    'hi': hello,
    'add': adding,
    'show': show,
    'find': find,
    'change': change,
    'birthday': birthday,
}

exit_commands = [
    'good bye',
    'exit',
    'close'
]


def main_example():
    filename = 'book.json'
    result = book.load_from_file(filename)
    if result:
        print(result)
        return

    while True:
        command, *data = input().strip().split(' ', 1)
        if command in exit_commands:
            print('Good Bye!')
            break
        elif (handler := commands.get(command)) is not None:
            if data:
                data = [str(x).strip() for x in data[0].split(',')]
            result = handler(command, *data)
        else:
            result = "Not correct command"
        print(result)

    book.save_to_file(filename)

if __name__ == "__main__":
    main_example()
