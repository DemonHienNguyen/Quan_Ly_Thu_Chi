from decimal import Decimal
from django import forms
from .models import Transaction, Budget, Category


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'amount', 'category', 'transaction_date', 'note']

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Số tiền giao dịch phải lớn hơn 0 VND.")
        return amount


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'monthly_limit', 'month', 'year']

    def clean_monthly_limit(self):
        limit = self.cleaned_data.get('monthly_limit')
        if limit is not None and limit <= 0:
            raise forms.ValidationError("Hạn mức ngân sách phải lớn hơn 0 VND.")
        return limit


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_name', 'type', 'icon']
