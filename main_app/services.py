"""
Утилиты для работы с API Битрикс24
"""
from django.utils import timezone
from datetime import timedelta
from integration_utils.bitrix24.models import BitrixUserToken


class BitrixEmployeeService:
    """Сервис для работы с сотрудниками через integration_utils"""

    def __init__(self, user_token: BitrixUserToken):
        self.user_token = user_token

    def get_all_departments(self):
        """
        Получить все подразделения
        """
        return self.user_token.call_api_method(
            'department.get',
            {
                'select': ['ID', 'NAME', 'UF_HEAD', 'PARENT']
            }
        )

    def get_department_employees(self, dept_id):
        """
        Получить сотрудников подразделения
        """
        return self.user_token.call_api_method(
            'im.department.employees.get',
            {
                'ID': [dept_id],
                'USER_DATA': 'Y'
            }
        )

    def get_department_managers(self, dept_id):
        """
        Получить руководителей подразделения
        """
        return self.user_token.call_api_method(
            'im.department.managers.get',
            {
                'ID': [dept_id],
                'USER_DATA': 'Y'
            }
        )

    def get_call_statistics(self, user_id, hours_back=24):
        """
        Получить статистику звонков пользователя
        """
        start_date = timezone.now() - timedelta(hours=hours_back)
        start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S')

        return self.user_token.call_api_method(
            'voximplant.statistic.get',
            {
                'FILTER': {
                    'PORTAL_USER_ID': user_id,
                    'CALL_TYPE': 1,
                    '>CALL_DURATION': 60,
                    '>CALL_START_DATE': start_date_str
                },
                'SORT': 'CALL_START_DATE',
                'ORDER': 'DESC'
            }
        )

    def get_employees_with_hierarchy(self):
        """
        Получить список сотрудников с иерархией руководителей и статистикой звонков
        """
        try:
            departments_response = self.get_all_departments()
            if not departments_response.get('result'):
                return []

            departments = departments_response['result']
            employees_data = []
            processed_users = set()

            for dept in departments:
                dept_id = dept['ID']
                dept_name = dept['NAME']

                employees_response = self.get_department_employees(dept_id)
                if not employees_response.get('result'):
                    continue

                dept_employees = employees_response['result'].get(str(dept_id))
                if not dept_employees:
                    continue

                managers = self._get_all_managers_hierarchy(dept_id)

                if isinstance(dept_employees, dict):
                    employees_list = [dept_employees]
                else:
                    employees_list = dept_employees

                for employee in employees_list:
                    user_id = int(employee['id'])

                    if user_id in processed_users:
                        continue
                    processed_users.add(user_id)

                    calls_count = self._get_employee_calls_count(user_id)

                    employee_data = {
                        'id': user_id,
                        'name': employee.get('first_name', ''),
                        'last_name': employee.get('last_name', ''),
                        'full_name': f"{employee.get('last_name', '')} {employee.get('first_name', '')}".strip(),
                        'position': employee.get('work_position', ''),
                        'department_name': dept_name,
                        'managers': managers,
                        'calls_count': calls_count
                    }

                    employees_data.append(employee_data)

            return employees_data

        except Exception as e:
            print(f"Ошибка при получении данных сотрудников: {e}")
            return []

    def _get_all_managers_hierarchy(self, dept_id):
        """
        Получить всех руководителей по иерархии (от ближайшего к самому верхнему)
        """
        managers = []
        current_dept_id = dept_id

        while current_dept_id:
            try:
                managers_response = self.get_department_managers(current_dept_id)
                if managers_response.get('result'):
                    dept_managers = managers_response['result'].get(str(current_dept_id))
                    if dept_managers:
                        if isinstance(dept_managers, dict):
                            managers_list = [dept_managers]
                        else:
                            managers_list = dept_managers

                        for manager in managers_list:
                            manager_name = f"{manager.get('last_name', '')} {manager.get('first_name', '')}".strip()
                            if manager_name and manager_name not in managers:
                                managers.append(manager_name)

                dept_response = self.user_token.call_api_method(
                    'department.get',
                    {
                        'ID': current_dept_id,
                        'select': ['PARENT']
                    }
                )

                if dept_response.get('result') and dept_response['result']:
                    parent_id = dept_response['result'][0].get('PARENT')
                    current_dept_id = parent_id
                else:
                    break

            except Exception as e:
                print(f"Ошибка при получении иерархии для подразделения {current_dept_id}: {e}")
                break

        return managers

    def get_active_users(self):
        """
        Получить список активных пользователей
        """
        try:
            return self.user_token.call_api_method(
                'user.get',
                {
                    'FILTER': {
                        'ACTIVE': True,
                        'USER_TYPE': 'employee'
                    },
                    'SORT': 'ID',
                    'ORDER': 'ASC'
                }
            )
        except Exception as e:
            print(f"Ошибка при получении списка активных пользователей: {e}")
            return {'result': []}

    def _get_employee_calls_count(self, employee_id):
        """Получение количества исходящих звонков > 1 минуты за последние 24 часа"""

        try:
            calls_response = self.get_call_statistics(employee_id)

            if calls_response.get('result'):
                return len(calls_response['result'])

            return 0

        except Exception as e:
            print(f"Ошибка при получении звонков для сотрудника {employee_id}: {e}")
            return 0