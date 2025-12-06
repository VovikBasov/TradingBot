#!/usr/bin/env python3
"""
Парсер для auto.ru - сбор марок и моделей автомобилей
"""

import requests
import csv
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

# Добавляем src в путь Python для импорта логгера
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import log

class AutoRuParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.base_url = "https://auto.ru"
        
    def get_page(self, url):
        """Получаем HTML страницу"""
        try:
            log.info(f"📄 Загружаем страницу: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            log.error(f"❌ Ошибка при загрузке страницы {url}: {e}")
            return None
    
    def parse_brands_and_models(self, url, vehicle_type):
        """Парсим марки и модели с указанной страницы"""
        html = self.get_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        brands_data = []
        
        # Ищем контейнер с марками (может быть в разных местах на странице)
        brand_selectors = [
            'select[name="mark"] option',
            '.Select[data-ga-name="mark"] option',
            '[data-ftid="sales__filter_mark"] option',
            'select[data-ftid="sales__filter_mark"] option'
        ]
        
        brand_options = None
        for selector in brand_selectors:
            brand_options = soup.select(selector)
            if brand_options:
                log.info(f"✅ Нашли селектор марок: {selector}")
                break
        
        if not brand_options:
            log.warning(f"⚠️ Не удалось найти список марок на странице {url}")
            # Попробуем найти ссылки на марки другим способом
            brand_links = soup.select('a[href*="/cars/"]')
            log.info(f"🔗 Найдено ссылок на марки: {len(brand_links)}")
            return []
        
        log.info(f"🏷️ Найдено марок: {len(brand_links)}")
        
        # Парсим каждую марку
        for option in brand_links:
            brand_name = option.get_text(strip=True)
            brand_value = option.get('value') or option.get('href', '')
            
            if not brand_name or brand_name in ['Любая', 'Все марки', '']:
                continue
                
            log.info(f"🔍 Обрабатываем марку: {brand_name}")
            
            # Получаем модели для этой марки
            models = self.get_models_for_brand(brand_name, brand_value, vehicle_type)
            
            for model_name in models:
                brands_data.append({
                    'brand': brand_name,
                    'model': model_name,
                    'vehicle_type': vehicle_type
                })
            
            # Задержка чтобы не перегружать сервер
            time.sleep(1)
        
        return brands_data
    
    def get_models_for_brand(self, brand_name, brand_value, vehicle_type):
        """Получаем список моделей для конкретной марки"""
        models = []
        
        # Формируем URL для страницы с моделями
        if 'cars' in vehicle_type.lower():
            model_url = f"https://auto.ru/nizhniy_novgorod/cars/{brand_name.lower()}/all/"
        else:
            model_url = f"https://auto.ru/nizhniy_novgorod/lcv/{brand_name.lower()}/all/"
        
        html = self.get_page(model_url)
        if not html:
            return models
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем селектор моделей
        model_selectors = [
            'select[name="model"] option',
            '.Select[data-ga-name="model"] option',
            '[data-ftid="sales__filter_model"] option',
            'select[data-ftid="sales__filter_model"] option'
        ]
        
        model_options = None
        for selector in model_selectors:
            model_options = soup.select(selector)
            if model_options:
                break
        
        if model_options:
            for option in model_options:
                model_name = option.get_text(strip=True)
                if model_name and model_name not in ['Любая', 'Все модели', '']:
                    models.append(model_name)
        
        log.info(f"   🚗 Найдено моделей для {brand_name}: {len(models)}")
        return models
    
    def save_to_csv(self, data, filename):
        """Сохраняем данные в CSV файл"""
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        filepath = os.path.join(desktop_path, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['brand', 'model', 'vehicle_type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            
            log.info(f"💾 Данные сохранены в: {filepath}")
            log.info(f"📊 Всего записей: {len(data)}")
            return True
            
        except Exception as e:
            log.error(f"❌ Ошибка при сохранении CSV: {e}")
            return False
    
    def run_parser(self):
        """Основная функция парсера"""
        log.info("🚗 Запускаем парсер Auto.ru...")
        
        all_data = []
        
        # Парсим легковые автомобили
        log.info("🔍 Парсим раздел 'Легковые авто'...")
        cars_url = "https://auto.ru/nizhniy_novgorod/cars/all/"
        cars_data = self.parse_brands_and_models(cars_url, "Легковой")
        all_data.extend(cars_data)
        
        # Парсим легкие коммерческие автомобили
        log.info("🔍 Парсим раздел 'Лёгкие коммерческие авто'...")
        lcv_url = "https://auto.ru/nizhniy_novgorod/lcv/all/"
        lcv_data = self.parse_brands_and_models(lcv_url, "Грузовой")
        all_data.extend(lcv_data)
        
        # Сохраняем результаты
        if all_data:
            self.save_to_csv(all_data, "auto_ru_brands_models.csv")
            log.info("✅ Парсинг завершен успешно!")
        else:
            log.error("❌ Не удалось собрать данные")
        
        return all_data

def main():
    """Точка входа"""
    try:
        parser = AutoRuParser()
        parser.run_parser()
        
    except Exception as e:
        log.error(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
