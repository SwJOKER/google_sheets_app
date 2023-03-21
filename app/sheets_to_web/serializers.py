from rest_framework import serializers
from .models import Sheet, Order, SheetError


class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ['row_index', 'order_index', 'cost', 'cost_ruble', 'delivery_date']


class ErrorsSerializer(serializers.ModelSerializer):

    class Meta:
        model = SheetError
        fields = ['error_text']


class SheetStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = Sheet
        fields = ['name', 'key', 'md5', 'available']


class SheetSerializer(serializers.ModelSerializer):
    orders = OrderSerializer(many=True)
    total_usd = serializers.SerializerMethodField()
    total_ruble = serializers.SerializerMethodField()
    errors_count = serializers.SerializerMethodField()

    class Meta:
        model = Sheet
        fields = ['name', 'orders', 'errors', 'total_usd', 'total_ruble', 'errors_count']

    def get_total_usd(self, instance):
        return instance.total_usd

    def get_total_ruble(self, instance):
        return instance.total_ruble

    def get_errors_count(self, instance):
        return instance.errors_count
