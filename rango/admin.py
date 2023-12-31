from django.contrib import admin
from rango.models import Category, Product, UserProfile, DummyReview, Article, Store
from django.conf import settings


class PageAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')


class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'email','latitude', 'longitude',)
    search_fields = ('name',)

    fieldsets = (
        (None, {
            'fields': ( 'name','email', 'latitude', 'longitude',)
        }),
    )


admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, PageAdmin)
admin.site.register(UserProfile)
admin.site.register(DummyReview)
admin.site.register(Article)
