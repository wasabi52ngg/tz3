import random
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from integration_utils.bitrix24.bitrix_user_auth.main_auth import main_auth
from django.conf import settings
from .services import BitrixEmployeeService


@main_auth(on_start=True, set_cookie=True)
def index(request):
    """Главная страница приложения"""
    app_settings = settings.APP_SETTINGS
    context = {
        'user': request.bitrix_user,
        'is_authenticated': True,
        'app_settings': app_settings
    }
    return render(request, 'main_app/index.html', context)


@main_auth(on_cookies=True)
def employees_table(request):
    """Представление для отображения таблицы сотрудников с руководителями и звонками"""
    
    try:
        service = BitrixEmployeeService(request.bitrix_user_token)
        employees_data = service.get_employees_with_hierarchy()
        
        context = {
            'employees': employees_data,
            'user': request.bitrix_user,
            'error_message': None,
        }
        
    except Exception as e:
        print(f"Ошибка в представлении employees_table: {e}")
        context = {
            'employees': [],
            'user': request.bitrix_user,
            'error_message': f"Ошибка загрузки данных: {str(e)}",
        }
    
    return render(request, 'main_app/employees_table.html', context)




@main_auth(on_cookies=True)
def generate_test_calls(request):
    """Скрипт для генерации тестовых данных о звонках"""
    
    try:
        service = BitrixEmployeeService(request.bitrix_user_token)
        
        users_response = service.get_active_users()
        
        if not users_response.get('result'):
            return JsonResponse({'status': 'error', 'message': 'Не удалось получить список пользователей'})
        
        users = users_response['result']
        created_calls = 0
        
        for user in users:
            user_id = int(user['ID'])

            calls_count = random.randint(1, 4)
            for i in range(calls_count):
                phone_number = f'+7(999)123-45-{i:02d}'
                call_duration = 120 + i * 30
                call_time = timezone.now() - timedelta(hours=i+1)
                
                register_data = {
                    'USER_ID': user_id,
                    'PHONE_NUMBER': phone_number,
                    'CALL_START_DATE': call_time.strftime('%Y-%m-%dT%H:%M:%S+03:00'),
                    'TYPE': 1,
                    'CRM_CREATE': 0,
                    'SHOW': 0,
                }
                
                register_response = request.bitrix_user_token.call_api_method('telephony.externalcall.register', register_data)
                
                if register_response.get('result'):
                    call_id = register_response['result']['CALL_ID']
                    
                    finish_data = {
                        'CALL_ID': call_id,
                        'USER_ID': user_id,
                        'DURATION': call_duration,
                        'COST': 5.50 + i,
                        'COST_CURRENCY': 'RUR',
                        'STATUS_CODE': '200',
                    }
                    
                    finish_response = request.bitrix_user_token.call_api_method('telephony.externalcall.finish', finish_data)
                    
                    if finish_response.get('result'):
                        created_calls += 1
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Создано {created_calls} тестовых звонков через API'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': f'Ошибка при создании тестовых звонков: {str(e)}'
        })
