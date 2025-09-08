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
            
            dept_map, parent_map = self._build_department_tree(departments)
            
            managers_map = self._get_map_managers(dept_map)
            
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
                    
                    is_department_head = self._is_department_head(dept, user_id)
                    
                    if is_department_head:
                        managers = self._get_managers_for_employee(dept_id, dept_map, managers_map, exclude_user_id=user_id, include_current_dept=False)
                    else:
                        managers = self._get_managers_for_employee(dept_id, dept_map, managers_map, exclude_user_id=user_id, include_current_dept=True)

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

    def _build_department_tree(self, departments):
        """
        Построить дерево отделов
        """
        dept_map = {dept['ID']: dept for dept in departments}
        parent_map = {}
        for dept in departments:
            parent_id = dept.get('PARENT')
            if parent_id:
                parent_map.setdefault(parent_id, []).append(dept['ID'])
        return dept_map, parent_map

    def _get_map_managers(self, dept_map):
        """
        Предзагрузить всех менеджеров всех отделов
        """
        managers_map = {}
        department_ids = list(dept_map.keys())
        
        try:
            response = self.user_token.call_api_method(
                'im.department.managers.get',
                {
                    'ID': department_ids,
                    'USER_DATA': 'Y'
                }
            )
            if response.get('result'):
                for dept_id, managers in response['result'].items():
                    dept_id = str(dept_id)
                    if isinstance(managers, dict):
                        managers = [managers]
                    managers_map[dept_id] = managers
        except Exception as e:
            print(f"Ошибка при предзагрузке менеджеров: {e}")
        return managers_map

    def _get_managers_for_employee(self, dept_id, dept_map, managers_map, exclude_user_id=None, include_current_dept=True):
        """
        Универсальный метод для получения руководителей сотрудника
        include_current_dept: True - включать текущий отдел, False - только родительские
        exclude_user_id: ID пользователя для исключения из списка
        """
        managers = []
        current_dept_id = dept_id
        
        if not include_current_dept:
            dept = dept_map.get(str(current_dept_id)) or dept_map.get(current_dept_id)
            if dept:
                current_dept_id = dept.get('PARENT')
            else:
                return managers
        
        while current_dept_id:
            dept_managers = managers_map.get(str(current_dept_id), [])
            
            for manager in dept_managers:
                manager_id = int(manager.get('id', 0))
                if exclude_user_id and manager_id == exclude_user_id:
                    continue
                manager_name = f"{manager.get('last_name', '')} {manager.get('first_name', '')}".strip()
                if manager_name and manager_name not in managers:
                    managers.append(manager_name)
            
            dept = dept_map.get(str(current_dept_id)) or dept_map.get(current_dept_id)
            if dept:
                current_dept_id = dept.get('PARENT')
            else:
                break
        
        return managers

    def _is_department_head(self, dept, user_id):
        """
        Проверить, является ли пользователь руководителем отдела
        """
        dept_head_id = dept.get('UF_HEAD')
        return dept_head_id and int(dept_head_id) == user_id

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