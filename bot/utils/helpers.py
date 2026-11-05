"""
Helper functions for the bot
"""
import os
import sys

def get_project_root():
    """Get the project root directory"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def format_number(number):
    """Format number with commas"""
    return f"{number:,.0f}"

def format_currency(amount, currency="ل.س"):
    """Format currency amount"""
    return f"{format_number(amount)} {currency}"