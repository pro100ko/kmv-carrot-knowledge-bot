from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from logging_config import admin_logger
from sqlite_db import db
from admin_panel import (
    is_admin,
    format_admin_message,
    format_error_message
)

# Create router for statistics
router = Router()

# States for statistics forms
class StatisticsForm(StatesGroup):
    period = State()
    type = State()

def collect_user_statistics(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Collect user statistics for the specified period"""
    try:
        # Get all users
        users = db.get_users(include_inactive=True)
        stats = []
        
        for user in users:
            # Get user activity
            activity = db.get_user_activity(user['id'])
            if not activity:
                continue
            
            # Filter activity by date
            period_activity = [
                a for a in activity 
                if start_date <= datetime.fromisoformat(a['timestamp']) <= end_date
            ]
            
            if not period_activity:
                continue
            
            # Get test attempts
            attempts = db.get_user_test_attempts(user['id'])
            period_attempts = [
                a for a in attempts 
                if start_date <= datetime.fromisoformat(a['timestamp']) <= end_date
            ]
            
            # Calculate statistics
            total_tests = len(period_attempts)
            successful_tests = sum(1 for a in period_attempts if a['is_successful'])
            total_score = sum(a['score'] for a in period_attempts)
            
            stats.append({
                'user_id': user['id'],
                'name': user['name'],
                'email': user.get('email', ''),
                'role': user.get('role', 'user'),
                'is_active': user['is_active'],
                'total_activity': len(period_activity),
                'last_activity': period_activity[-1]['timestamp'],
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': (successful_tests / total_tests * 100) if total_tests else 0,
                'average_score': total_score / total_tests if total_tests else 0
            })
        
        return pd.DataFrame(stats)
    
    except Exception as e:
        admin_logger.error(f"Error collecting user statistics: {e}")
        raise

def collect_test_statistics(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Collect test statistics for the specified period"""
    try:
        # Get all tests
        tests = db.get_tests(include_inactive=True)
        stats = []
        
        for test in tests:
            # Get test attempts
            attempts = db.get_test_attempts(test['id'])
            period_attempts = [
                a for a in attempts 
                if start_date <= datetime.fromisoformat(a['timestamp']) <= end_date
            ]
            
            if not period_attempts:
                continue
            
            # Calculate statistics
            total_attempts = len(period_attempts)
            successful_attempts = sum(1 for a in period_attempts if a['is_successful'])
            total_score = sum(a['score'] for a in period_attempts)
            total_time = sum(a['time_taken'] for a in period_attempts)
            
            stats.append({
                'test_id': test['id'],
                'name': test['name'],
                'is_active': test['is_active'],
                'passing_score': test['passing_score'],
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'success_rate': (successful_attempts / total_attempts * 100) if total_attempts else 0,
                'average_score': total_score / total_attempts if total_attempts else 0,
                'average_time': total_time / total_attempts if total_attempts else 0
            })
        
        return pd.DataFrame(stats)
    
    except Exception as e:
        admin_logger.error(f"Error collecting test statistics: {e}")
        raise

def export_to_excel(df: pd.DataFrame, filename: str) -> BytesIO:
    """Export DataFrame to Excel file"""
    try:
        # Create Excel writer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write DataFrame to Excel
            df.to_excel(writer, sheet_name='Statistics', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Statistics']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'bg_color': '#D9E1F2',
                'border': 1
            })
            
            # Format headers
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)  # Set column width
        
        # Reset buffer position
        output.seek(0)
        return output
    
    except Exception as e:
        admin_logger.error(f"Error exporting to Excel: {e}")
        raise

# Command handlers
@router.message(Command("export_stats"))
async def export_stats_command(message: Message) -> None:
    """Handle /export_stats command (admin only)"""
    try:
        if not is_admin(message.from_user.id):
            await message.answer(
                format_error_message("У вас нет доступа к этой команде"),
                parse_mode="HTML"
            )
            return
        
        # Get command arguments
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args or args[0] not in ['users', 'tests']:
            await message.answer(
                format_admin_message(
                    title="📊 Экспорт статистики",
                    content="Используйте команду в формате:\n/export_stats <users|tests>"
                )
            )
            return
        
        stats_type = args[0]
        
        # Set default period (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Collect statistics
        if stats_type == 'users':
            df = collect_user_statistics(start_date, end_date)
            filename = f"user_statistics_{end_date.strftime('%Y%m%d')}.xlsx"
        else:  # tests
            df = collect_test_statistics(start_date, end_date)
            filename = f"test_statistics_{end_date.strftime('%Y%m%d')}.xlsx"
        
        if df.empty:
            await message.answer(
                format_admin_message(
                    title="📊 Экспорт статистики",
                    content="За указанный период нет данных для экспорта."
                )
            )
            return
        
        # Export to Excel
        excel_file = export_to_excel(df, filename)
        
        # Send file
        await message.answer_document(
            document=excel_file,
            filename=filename,
            caption=format_admin_message(
                title="📊 Статистика экспортирована",
                content=f"Статистика за период с {start_date.strftime('%d.%m.%Y')} "
                       f"по {end_date.strftime('%d.%m.%Y')} успешно экспортирована."
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in export stats command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        ) 