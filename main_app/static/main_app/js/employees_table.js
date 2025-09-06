// JavaScript для таблицы сотрудников

// Инициализация BX24
BX24.init(function() {
    console.log('BX24 SDK инициализирован');
});

// Функция для открытия профиля сотрудника в слайдере
function openEmployeeProfile(userId) {
    if (typeof BX24 !== 'undefined' && BX24.openPath) {
        const path = `/company/personal/user/${userId}/`;
        
        BX24.openPath(path, function(result) {
            if (result.result === 'error') {
                console.error('Ошибка открытия профиля:', result);
                showNotification('Ошибка при открытии профиля сотрудника', 'error');
            } else if (result.result === 'close') {
                console.log('Слайдер закрыт');
            }
        });
    } else {
        console.error('BX24 SDK не доступен');
        showNotification('BX24 SDK не доступен. Откройте приложение в Bitrix24.', 'error');
    }
}

// Функция для генерации тестовых звонков
function generateTestCalls() {
    const button = event.target;
    const originalText = button.textContent;
    
    button.disabled = true;
    button.textContent = 'Генерация...';
    
    fetch('/generate-test-calls/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification(data.message, 'success');
            // Обновляем страницу через 2 секунды
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        showNotification('Произошла ошибка при генерации тестовых звонков', 'error');
    })
    .finally(() => {
        button.disabled = false;
        button.textContent = originalText;
    });
}

// Функция для показа уведомлений
function showNotification(message, type = 'info') {
    const modal = new bootstrap.Modal(document.getElementById('notificationModal'));
    const messageElement = document.getElementById('notificationMessage');
    
    messageElement.innerHTML = message;
    
    // Добавляем классы в зависимости от типа
    const modalContent = document.querySelector('#notificationModal .modal-content');
    modalContent.className = 'modal-content';
    
    if (type === 'success') {
        modalContent.classList.add('border-success');
    } else if (type === 'error') {
        modalContent.classList.add('border-danger');
    } else if (type === 'warning') {
        modalContent.classList.add('border-warning');
    }
    
    modal.show();
}

// Функция для получения CSRF токена
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Добавляем стили для ссылок сотрудников
document.addEventListener('DOMContentLoaded', function() {
    const employeeLinks = document.querySelectorAll('.employee-link');
    employeeLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            this.style.cursor = 'pointer';
        });
    });
});
