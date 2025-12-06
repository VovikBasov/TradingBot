#!/usr/bin/env python3
"""
Упрощенный парсер для auto.ru
"""

import requests
import csv
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import log

class SimpleAutoRuParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
    
    def get_api_data(self, category):
        """Получаем данные через API auto.ru"""
        url = f"https://auto.ru/-/ajax/desktop/listing/"
        params = {
            'section': 'all',
            'category': category,
            'sort': 'fresh_relevance_1-desc'
        }
        
        try:
            log.info(f"🔧 Запрашиваем данные API для категории: {category}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            log.error(f"❌ Ошибка API для {category}: {e}")
            return None
    
    def extract_brands_from_api(self, api_data, vehicle_type):
        """Извлекаем бренды из API данных"""
        brands_data = []
        
        if not api_data or 'state' not in api_data:
            return brands_data
        
        state = api_data['state']
        
        # Пробуем разные пути к данным о брендах
        possible_paths = [
            state.get('listing', {}).get('data', {}).get('filters', {}).get('mark', []),
            state.get('filters', {}).get('mark', []),
            state.get('mark', [])
        ]
        
        marks = []
        for path in possible_paths:
            if path and isinstance(path, list) and len(path) > 0:
                marks = path
                break
        
        log.info(f"🏷️ Найдено марок в API: {len(marks)}")
        
        for mark in marks:
            if isinstance(mark, dict):
                brand_name = mark.get('name', mark.get('title', ''))
                if brand_name and brand_name not in ['Любая', 'Все марки']:
                    # Для упрощения добавляем марку без моделей
                    brands_data.append({
                        'brand': brand_name,
                        'model': 'Все модели',
                        'vehicle_type': vehicle_type
                    })
        
        return brands_data
    
    def run_parser(self):
        """Запускаем парсер"""
        log.info("🚗 Запускаем упрощенный парсер Auto.ru...")
        
        all_data = []
        
        # Легковые автомобили
        cars_data = self.get_api_data('cars')
        if cars_data:
            cars_brands = self.extract_brands_from_api(cars_data, "Легковой")
            all_data.extend(cars_brands)
        
        time.sleep(2)  # Задержка между запросами
        
        # Коммерческие автомобили
        lcv_data = self.get_api_data('lcv')
        if lcv_data:
            lcv_brands = self.extract_brands_from_api(lcv_data, "Грузовой")
            all_data.extend(lcv_brands)
        
        # Сохраняем в CSV
        if all_data:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop_path, "auto_ru_brands_simple.csv")
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['brand', 'model', 'vehicle_type'])
                writer.writeheader()
                writer.writerows(all_data)
            
            log.info(f"💾 Данные сохранены в: {filepath}")
            log.info(f"📊 Всего записей: {len(all_data)}")
        else:
            log.error("❌ Не удалось собрать данные")
        
        return all_data

def main():
    try:
        parser = SimpleAutoRuParser()
        parser.run_parser()
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
